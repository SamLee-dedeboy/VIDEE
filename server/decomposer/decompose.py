from custom_types import Node
import AutoGenUtils.query as autogen_utils


async def goal_decomposition(goal: str) -> list[Node]:
    decomposed_steps = await autogen_utils.run_goal_decomposition_agent(goal=goal)
    decomposed_steps = add_uids(decomposed_steps)
    return decomposed_steps


async def task_decomposition(task: str, current_steps: list[Node]) -> list[Node]:
    decomposed_steps = await autogen_utils.run_task_decomposition_agent(task=task)
    decomposed_steps = add_uids(decomposed_steps)
    # modifies current_steps
    find_and_replace(decomposed_steps, task["label"], current_steps)
    return current_steps


def find_and_replace(decomposed_steps, task_label, current_steps):
    # find the task label in the current steps using dfs recursively
    # if the task is found, replace it with the decomposed steps
    # if the task is not found, return None
    # here is the code
    for step in current_steps:
        if step["label"] == task_label:
            step["children"] = decomposed_steps
            decomposed_from_id = step["id"]
            for child in decomposed_steps:
                child["id"] = f"{decomposed_from_id}-{child['id']}"
                child["parentIds"] = [
                    f"{decomposed_from_id}-{parent_id}"
                    for parent_id in child["parentIds"]
                ]
            step["children"] = decomposed_steps
            return
        elif "children" in step:
            find_and_replace(decomposed_steps, task_label, step["children"])
        else:
            continue
    return None


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
    # Add unique ids to each step using bfs on children
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
        if "children" in step:
            queue.extend(step["children"])
    return unique_steps


def flatten_children(data):
    """
    Recursively flattens the children of the given data structure.

    Args:
        data (dict): A dictionary containing an 'id' and a list of 'children'.

    Returns:
        list: A list of all ids, including the current id and all children ids.
    """
    result = [data]  # Start with the current id
    for child in data.get("children", []):  # Iterate over the children
        result.extend(flatten_children(child))  # Recursively flatten children
    return result
