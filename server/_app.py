from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from collections import defaultdict
from openai import OpenAI
import AutoGenUtils.query as autogen_utils

# Initialize the Flask app and CORS
app = Flask(__name__)
CORS(app)

dirname = os.path.dirname(__file__)
relative_path = lambda filename: os.path.join(dirname, filename)
client = OpenAI(api_key=open("api_key").read(), timeout=10)


@app.route("/test/")
def test():
    return "Hello Task Decomposition"


@app.route("/goal_decomposition/", methods=["POST"])
async def goal_decomposition():
    goal = request.json["goal"]
    # decomposed_steps = await autogen_utils.run_goal_decomposition_agent(goal=goal)
    # save_json(decomposed_steps, "test_decomposed_steps.json")
    decomposed_steps = json.load(
        open(relative_path("test_decomposed_steps_w_children.json"))
    )
    # decomposed_steps = add_uids(decomposed_steps)
    # save_json(decomposed_steps, "test_decomposed_steps.json")
    return json.dumps(decomposed_steps)


@app.route("/task_decomposition/", methods=["POST"])
async def task_decomposition():
    task = request.json["task"]
    decomposed_steps = await autogen_utils.run_task_decomposition_agent(task=task)
    decomposed_steps = add_uids(decomposed_steps)
    save_json(decomposed_steps, "test_decomposed_one_step.json")
    decomposed_steps = json.load(open(relative_path("test_decomposed_one_step.json")))

    # save the decomposed pipeline
    # task["children"] = decomposed_steps
    current_steps = json.load(
        open(relative_path("test_decomposed_steps_w_children.json"))
    )
    flatten_current_steps = flatten_children({"id": "root", "children": current_steps})[
        1:
    ]
    save_json(flatten_current_steps, "test_flatten_current_steps.json")
    # replace the task with the decomposed steps
    decomposed_step_index = next(
        (
            i
            for i, item in enumerate(flatten_current_steps)
            if item["label"] == task["label"]
        ),
        -1,
    )
    decomposed_from_id = flatten_current_steps[decomposed_step_index]["id"]
    for child in decomposed_steps:
        child["id"] = f"{decomposed_from_id}-{child['id']}"
        child["parentIds"] = [
            f"{decomposed_from_id}-{parent_id}" for parent_id in child["parentIds"]
        ]
    flatten_current_steps[decomposed_step_index]["children"] = decomposed_steps

    save_json(current_steps, "test_decomposed_steps_w_children.json")
    return json.dumps(current_steps)


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


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    app.run(debug=True)
