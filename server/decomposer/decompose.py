from server.custom_types import Node, PrimitiveTaskDescription
import server.AutoGenUtils.query as autogen_utils
import random
import copy
from collections import defaultdict
import json


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


async def goal_decomposition(goal: str, model: str, api_key: str) -> list[Node]:
    decomposed_semantic_tasks = await autogen_utils.run_goal_decomposition_agent(
        goal=goal, model=model, api_key=api_key
    )
    for index, task in enumerate(decomposed_semantic_tasks):
        task["confidence"] = random.random()
        task["complexity"] = random.random()
        decomposed_semantic_tasks[index] = task
    decomposed_semantic_tasks = add_parents_and_children(decomposed_semantic_tasks)
    return decomposed_semantic_tasks


async def task_decomposition(
    task: Node, current_steps: list[Node], model: str, api_key: str
) -> list[Node]:
    decomposed_semantic_tasks = await autogen_utils.run_task_decomposition_agent(
        task=task, model=model, api_key=api_key
    )
    decomposed_semantic_tasks = add_parents_and_children(decomposed_semantic_tasks)
    for index in range(len(decomposed_semantic_tasks)):
        decomposed_semantic_tasks[index]["confidence"] = random.random()
        decomposed_semantic_tasks[index]["complexity"] = random.random()
    # decomposed_steps = add_uids(decomposed_steps)
    # modifies current_steps
    result = find_and_replace(decomposed_semantic_tasks, task["label"], current_steps)
    return current_steps


async def one_shot_decomposition_to_primitive_task(
    semantic_tasks: list[Node],
    primitive_task_list: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
) -> list:
    """Decompose a list of semantic tasks into primitive tasks.
    Args:
        semantic_tasks (list[Node]): A list of semantic tasks to decompose.
        primitive_task_list (list[PrimitiveTaskDescription]): A list of primitive tasks.
        model (str): The model to use for decomposition.
        api_key (str): The API key to use for decomposition.
        target_task (str): The target task to decompose. If None, decompose all tasks.
    """
    decomposed_primitive_tasks = (
        await autogen_utils.run_stepped_decomposition_to_primitive_task_agent(
            tree=semantic_tasks,
            primitive_task_list=primitive_task_list,
            model=model,
            api_key=api_key,
        )
    )
    decomposed_primitive_tasks = add_parents_and_children(decomposed_primitive_tasks)
    decomposed_primitive_tasks = add_root(decomposed_primitive_tasks)
    # decomposed_primitive_tasks = add_uids(decomposed_primitive_tasks)
    return decomposed_primitive_tasks


async def stream_decomposition_to_primitive_tasks(
    semantic_tasks: list[Node],
    primitive_task_list: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
):
    """Decompose a list of semantic tasks into primitive tasks.
    Args:
        semantic_tasks (list[Node]): A list of semantic tasks to decompose.
        primitive_task_list (list[PrimitiveTaskDescription]): A list of primitive tasks.
        model (str): The model to use for decomposition.
        api_key (str): The API key to use for decomposition.
        target_task (str): The target task to decompose. If None, decompose all tasks.
    """
    # try:
    semantic_tasks = sorted(semantic_tasks, key=lambda x: x.id)
    for i, semantic_task in enumerate(semantic_tasks):
        done_tasks = semantic_tasks[:i]
        decomposed_primitive_tasks = (
            await autogen_utils.run_decomposition_to_primitive_task_agent(
                task=semantic_task,
                done_tasks=done_tasks,
                primitive_task_list=primitive_task_list,
                model=model,
                api_key=api_key,
            )
        )
        # remap id
        for i, step in enumerate(decomposed_primitive_tasks):
            step["id"] = f"{semantic_task.id}-{step['id']}"
            step["depend_on"] = list(
                map(lambda d: f"{semantic_task.id}-{d}", step.get("depend_on", []))
            )
            decomposed_primitive_tasks[i] = step
        decomposed_primitive_tasks = add_parents_and_children(
            decomposed_primitive_tasks
        )
        yield semantic_task, decomposed_primitive_tasks
    # except Exception as e:
    #     print(f"Error in stream_decomposition_to_primitive_tasks: {e}")
    #     yield []
    pass


def find_and_replace(decomposed_steps, task_label, current_steps):
    # find the task label in the current steps using dfs recursively
    # if the task is found, replace it with the decomposed steps
    # if the task is not found, return None
    for step in current_steps:
        if step["label"] == task_label:
            step["sub_tasks"] = decomposed_steps
            decomposed_from_id = step["id"]
            START_id = task_label + "-sub_tasks-" + "START"
            END_id = task_label + "-sub_tasks-" + "END"
            task_START = {
                "id": START_id,
                "label": "START",
                "description": "START",
                "explanation": "N/A",
                "parentIds": [decomposed_from_id],
                "children": [],
                "sub_tasks": [],
                "confidence": 0.0,
                "complexity": 0.0,
            }

            task_END = {
                "id": END_id,
                "label": "END",
                "description": "END",
                "explanation": "N/A",
                "parentIds": [decomposed_from_id],
                "children": [decomposed_from_id],
                "sub_tasks": [],
                "confidence": 0.0,
                "complexity": 0.0,
            }
            for i, child in enumerate(decomposed_steps):
                child["id"] = f"{decomposed_from_id}-{child['id']}"
                if child["parentIds"] == []:
                    # child["parentIds"] = [decomposed_from_id]
                    child["parentIds"] = [START_id]
                    task_START["children"].append(child["id"])
                else:
                    child["parentIds"] = [
                        f"{decomposed_from_id}-{parent_id}"
                        for parent_id in child["parentIds"]
                    ]

                if child["children"] == []:
                    child["children"] = [END_id]
                    task_END["parentIds"].append(child["id"])
                decomposed_steps[i] = child
            decomposed_steps.insert(0, task_START)
            decomposed_steps.append(task_END)
            step["sub_tasks"] = decomposed_steps
            return "found and replaced"
        elif "sub_tasks" in step:
            find_and_replace(decomposed_steps, task_label, step["sub_tasks"])
        else:
            continue
    return None


def prune_redundant_parents(decomposed_steps):
    # Step 1: Build a mapping from each item ID to its parents
    parent_map = {
        str(item["id"]): set(list(map(lambda id: str(id), item["parentIds"])))
        for item in decomposed_steps
    }

    # Step 2: Iterate through each item's parents and remove redundant ones
    for item_id, parents in parent_map.items():
        to_remove = set()
        for parent in parents:
            if parent in parent_map:  # Check if parent itself has parents
                to_remove.update(
                    parent_map[parent]
                )  # Mark parent's parents as redundant

        parent_map[item_id] -= to_remove  # Remove redundant parents

    # Step 3: Update the original list with pruned parent IDs
    for item in decomposed_steps:
        item["parentIds"] = list(parent_map[item["id"]])

    return decomposed_steps


def add_parents_and_children(decomposed_steps):
    children_dict = defaultdict(list)
    for i, step in enumerate(decomposed_steps):
        step["id"] = str(step["id"])
        step["depend_on"] = list(map(lambda d: str(d), step.get("depend_on", [])))
        step["parentIds"] = copy.deepcopy(step.get("depend_on", []))
        del step["depend_on"]
        step["children"] = []
        step["sub_tasks"] = []
        for parent in step["parentIds"]:
            children_dict[parent].append(step["id"])
        decomposed_steps[i] = step
    for i, step in enumerate(decomposed_steps):
        step["children"] = children_dict[step["id"]]
        decomposed_steps[i] = step
    return decomposed_steps


def add_root(decomposed_steps):
    root_step = {
        "id": "-1",
        "label": "Root",
        "description": "Root",
        "explanation": "N/A",
        "parentIds": [],
        "children": [],
        "sub_tasks": [],
    }
    decomposed_steps.append(root_step)
    return decomposed_steps


def add_orders(decomposed_steps):
    order_dict = {}
    for step in decomposed_steps:
        label = step["label"]
        if step["depend_on"] == []:
            step["order"] = 0
            order_dict[label] = step["order"]
        else:
            dependent_order = max(list(map(lambda x: order_dict[x], step["depend_on"])))
            step["order"] = dependent_order + 1
            order_dict[label] = step["order"]
    return decomposed_steps


def add_uids(decomposed_steps):
    id_dict = {}
    # Add unique ids to each step using bfs on sub_tasks
    uid = 0
    queue = decomposed_steps
    unique_steps = []
    while queue:
        step = queue.pop(0)
        step["id"] = str(uid)
        id_dict[step["label"]] = step["id"]
        depend_steps = step.get("depend_on", [])
        depend_steps = list(map(lambda label: id_dict[label], depend_steps))
        step["parentIds"] = depend_steps
        unique_steps.append(step)
        uid += 1
        if "sub_tasks" in step:
            queue.extend(step["sub_tasks"])
    return unique_steps


def flatten_sub_tasks(data):
    """
    Recursively flattens the sub_tasks of the given data structure.

    Args:
        data (dict): A dictionary containing an 'id' and a list of 'sub_tasks

    Returns:
        list: A list of all ids, including the current id and all sub_tasks ids.
    """
    result = [data]  # Start with the current id
    for child in data.get("sub_tasks", []):  # Iterate over the sub_tasks
        result.extend(flatten_sub_tasks(child))  # Recursively flatten sub_tasks
    return result