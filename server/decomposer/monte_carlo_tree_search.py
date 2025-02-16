import random
from pydantic import BaseModel
import math
import random
from server.AutoGenUtils import query
from server.custom_types.custom_types import MCT_Node
import server.evaluator as evaluator


MAX_STEPS = 10


def init_MCTS():
    root = MCT_Node(
        id="root",
        label="Root",
        MCT_id="-1",
        print_label="Root",
        description="Root node",
        explanation="Root node",
        parentIds=[],
        MCT_parent_id=None,
    )
    return root


# def collect_MCT_node_dict(root: MCT_Node):
#     node_dict = {}
#     queue = [root]
#     while queue:
#         node = queue.pop(0)
#         node_dict[node.MCT_id] = node
#         queue += list(map(lambda id: node_dict[id], node.MCT_children_ids))
#     return node_dict


async def stream_MCTS(
    root,
    node_dict,
    goal: str,
    model: str,
    api_key: str,
    next_selection=None,
):
    try:
        while True:
            root = await MCTS_step(
                root,
                node_dict,
                next_selection=next_selection,
                goal=goal,
                model=model,
                api_key=api_key,
            )
            next_selection = select(root, node_dict)
            max_value_path = get_max_value_path(root, node_dict)
            yield root, next_selection, max_value_path
            if all_END(root, node_dict):
                yield root, None, None
    except Exception as e:
        print(f"Error in stream_MCTS: {e}")
        yield root, None, None
    pass


async def MCTS_step(
    root: MCT_Node,
    node_dict: dict,
    goal: str,
    model: str,
    api_key: str,
    next_selection=None,
    evaluator_definitions=None,
) -> MCT_Node:
    try:
        # select a node to expand
        if next_selection is None:
            node = select(root, node_dict)
        else:
            node = node_dict[next_selection.MCT_id]
        # expand the node with children
        children = await expand(node, node_dict, goal, model, api_key)
        # run evaluation on *ALL* the children
        reward_value_list = await reward(
            goal,
            children,
            node_dict,
            model=model,
            api_key=api_key,
            evaluator_definitions=evaluator_definitions,
        )
        # backpropagate the reward values
        for child, reward_value in zip(children, reward_value_list):
            backpropagate(child, reward_value, node_dict)
        return root
    except Exception as e:
        print(f"Error in MCTS_step: {e}")
        return root


def UCT(node: MCT_Node, parent_node: MCT_Node | None, exploration_weight=1.41) -> float:
    """Upper Confidence Bound for Trees (UCT) selection"""
    if node.visits == 0:
        return float("inf")  # Prioritize unvisited nodes
    if node.label == "END":
        return float("-inf")
    if parent_node is None:
        parent_visits = 1
    else:
        parent_visits = parent_node.visits
    return (node.value / node.visits) + exploration_weight * (
        math.sqrt(math.log(parent_visits) / node.visits)
    )


def select(node: MCT_Node, node_dict: dict) -> MCT_Node:
    while node.MCT_children_ids:
        parent_node = node_dict[node.MCT_parent_id] if node.MCT_parent_id else None
        candidate_children_ids = list(
            filter(
                lambda id: not node_dict[id].children_all_ends, node.MCT_children_ids
            )
        )
        if not candidate_children_ids:
            break  # this means the MCTS simulation is finished
        node = max(
            list(map(lambda node_id: node_dict[node_id], candidate_children_ids)),
            key=lambda node: UCT(node, parent_node),
        )
    return node


async def expand(
    parent_node: MCT_Node, node_dict: dict, goal: str, model: str, api_key: str, n=2
) -> MCT_Node:
    """Expands the node by adding one of its possible children"""

    # new_node = MCT_Node(id=f"{parent_node.MCT_id}/{-1}", label="END", description="END", explanation="END", parentIds=[parent_node.MCT_id], MCT_id=f"{parent_node.MCT_id}/{-1}", MCT_parent_id=parent_node.MCT_id)
    # node_dict[new_node.MCT_id] = new_node
    # parent_node.MCT_children_ids.append(new_node.MCT_id)
    # return new_node
    try:
        previous_steps = get_previous_steps(parent_node, node_dict)
        if not is_END(parent_node):
            children = await query.run_goal_decomposition_agent_stepped(
                goal,
                previous_steps,
                model=model,
                api_key=api_key,
                temperature=1.0,
                n=n,
                remain_steps=MAX_STEPS - parent_node.level,
            )
            for index, child_node in enumerate(children):
                child_as_MCT_node = MCT_Node(
                    **child_node,
                    MCT_id=f"{parent_node.MCT_id}/{index}",
                    print_label=f"{child_node['label']} (0/0)",
                    MCT_parent_id=parent_node.MCT_id,
                    level=parent_node.level + 1,
                )
                node_dict[child_as_MCT_node.MCT_id] = child_as_MCT_node
                parent_node.MCT_children_ids.append(child_as_MCT_node.MCT_id)
            update_end_paths(parent_node, node_dict)

            return [node_dict[child_id] for child_id in parent_node.MCT_children_ids]
            # return node_dict[random.choice(parent_node.MCT_children_ids)]
        return parent_node  # No expansion if node is terminal
    except Exception as e:
        print(f"Error in expand: {e}")


def update_end_paths(node: MCT_Node, node_dict: dict):
    while node is not None:
        if all_END(node, node_dict):
            node.children_all_ends = True
        else:
            break
        node = node_dict[node.MCT_parent_id] if node.MCT_parent_id else None


async def reward(
    goal: str,
    children: list[MCT_Node],
    node_dict,
    model: str,
    api_key: str,
    evaluator_definitions=None,
) -> float:
    """Evaluates the children nodes and returns the reward value for each child in parallel"""
    try:
        reward_value_list = []
        eval_params = []
        # collect execution parameters for all children
        for node in children:
            node_str = task_def_toString(node, goal)
            parent_node_str = task_def_toString(node_dict[node.MCT_parent_id], goal)
            eval_params.append((goal, node_str, parent_node_str))

        # runs evaluation on all children in parallel
        eval_results = await evaluator.run_all_evaluations(
            eval_params=eval_params,
            model=model,
            api_key=api_key,
        )

        # update the eval results for each child
        for node, eval_result in zip(children, eval_results):
            [
                node.llm_evaluation.complexity,
                node.llm_evaluation.coherence,
                node.llm_evaluation.importance,
            ] = eval_result
            reward_value = (
                node.llm_evaluation.complexity
                + node.llm_evaluation.coherence
                + node.llm_evaluation.importance
            ) / 3

            node.llm_evaluation.complexity = bool(node.llm_evaluation.complexity)
            node.llm_evaluation.coherence = bool(node.llm_evaluation.coherence)
            node.llm_evaluation.importance = bool(node.llm_evaluation.importance)

            node.user_evaluation.complexity = node.llm_evaluation.complexity
            node.user_evaluation.coherence = node.llm_evaluation.coherence
            node.user_evaluation.importance = node.llm_evaluation.importance
            reward_value_list.append(reward_value)
        return reward_value_list
    except Exception as e:
        print(f"Error in reward: {e}")


def backpropagate(node: MCT_Node, reward: float, node_dict: dict) -> None:
    """Updates the tree with the simulation results"""
    while node is not None:
        node.visits += 1
        node.value += reward  # Should we do some normalization here to avoid inflation?
        node.print_label = f"{node.label} ({node.value}/{node.visits})"
        node = node_dict[node.MCT_parent_id] if node.MCT_parent_id else None


# def best_child(node: MCT_Node, node_dict: dict) -> MCT_Node:
#     return max(list(map(lambda id: node_dict[id], node.MCT_children_ids)), key=lambda c: c.visits) # most visits or highest value?


def get_max_value_path(root: MCT_Node, node_dict: dict):
    # dfs recursively to get all the leaf paths with accumulated values
    paths = []
    stack = [(root, 1)]
    while stack:
        node, accumulated_value = stack.pop()
        if not node.MCT_children_ids:
            path_ids = list(
                map(
                    lambda parent: parent["MCT_id"], get_previous_steps(node, node_dict)
                )
            )
            paths.append((path_ids + ["-1"], accumulated_value))
        for child_id in node.MCT_children_ids:
            stack.append(
                (node_dict[child_id], accumulated_value * node_dict[child_id].value)
            )
    max_value_path = max(paths, key=lambda x: x[1])
    return max_value_path


def get_previous_steps(node: MCT_Node, node_dict: dict) -> list[dict]:
    steps = []
    while node.MCT_parent_id:
        steps.append(dict(node))
        node = node_dict[node.MCT_parent_id]
    return steps


def is_END(node: MCT_Node):
    return node.label == "END"


def all_END(node: MCT_Node, node_dict: dict):
    # dfs to check if all paths end in END
    if not node.MCT_children_ids:
        return is_END(node)
    return all(all_END(node_dict[child], node_dict) for child in node.MCT_children_ids)


def task_def_toString(task: MCT_Node, goal: str):
    if task.MCT_id == "-1":
        return goal
    return """
    Task: {label}
    Description: {description}
    """.format(
        label=task.label, description=task.description
    )


from treelib import Node, Tree


def visualize_tree(root: MCT_Node, node_dict: dict):
    tree = Tree()
    # bread-first traversal
    queue = [root]
    while queue:
        node = queue.pop(0)
        tree.create_node(node.print_label, node.MCT_id, parent=node.MCT_parent_id)
        queue += list(map(lambda id: node_dict[id], node.MCT_children_ids))
    print(tree.show(stdout=False))
