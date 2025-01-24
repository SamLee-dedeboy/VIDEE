from typing import Union
from fastapi import FastAPI, Request
import json
import os
from collections import defaultdict
from typing import Callable
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware

# local packages
import server.custom_types as custom_types
import server.decomposer as decomposer
import server.executor as executor

app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dirname = os.path.dirname(__file__)
relative_path = lambda filename: os.path.join(dirname, filename)
api_key = open(relative_path("api_key")).read()
default_model = "gpt-4o-mini"

dev = True


@app.get("/test/")
def test():
    return "Hello Task Decomposition"


@app.post("/goal_decomposition/")
async def goal_decomposition(request: Request) -> list[custom_types.Node]:
    goal = await request.body()
    goal = json.loads(goal)["goal"]
    if dev:
        decomposed_steps = json.load(
            open(relative_path("test_decomposed_steps_w_children.json"))
        )
    else:
        decomposed_steps = await decomposer.goal_decomposition(
            goal, model=default_model, api_key=api_key
        )
        save_json(
            decomposed_steps, relative_path("test_decomposed_steps_w_children.json")
        )
    return decomposed_steps


@app.post("/semantic_task/task_decomposition/")
async def task_decomposition(request: Request) -> list[custom_types.Node]:
    request = await request.body()
    request = json.loads(request)
    task = request["task"]
    current_steps = request["current_steps"]
    if False:
        current_steps = json.load(
            open(relative_path("test_decomposed_steps_w_children.json"))
        )
    else:
        # modifies current_steps
        current_steps = await decomposer.task_decomposition(
            task, current_steps, model=default_model, api_key=api_key
        )
        save_json(current_steps, relative_path("test_decomposed_steps_w_children.json"))
    return current_steps


@app.post("/semantic_task/decomposition_to_elementary_tasks/")
async def task_decomposition(request: Request) -> list:
    request = await request.body()
    request = json.loads(request)
    task = request["task"]
    current_steps = request["current_steps"]
    elementary_task_list = json.load(
        open(relative_path("decomposer/elementary_task_defs.json"))
    )
    if dev:
        decomposed_elementary_tasks = json.load(
            open(relative_path("test_elementary_tasks.json"))
        )
    else:
        decomposed_elementary_tasks = await decomposer.decomposition_to_elementary_task(
            task,
            current_steps,
            elementary_task_list,
            model=default_model,
            api_key=api_key,
        )
        save_json(
            decomposed_elementary_tasks, relative_path("test_elementary_tasks.json")
        )
    return decomposed_elementary_tasks


@app.post("/semantic_task/delete_children/")
async def task_decomposition(request: Request) -> list:
    request = await request.body()
    request = json.loads(request)
    task = request["task"]
    current_steps = request["current_steps"]
    dfs_find_and_do(
        current_steps, task["id"], lambda step: step.update({"children": []})
    )
    # save_json(current_steps, "test_decomposed_steps_w_children.json")
    return current_steps


@app.post("/elementary_task/execution_graph/")
async def execute_elementary_tasks(request: Request) -> list:
    request = await request.body()
    request = json.loads(request)
    tasks = request["tasks"]
    execution_graph = await executor.create_graph(tasks)

    # save_json(current_steps, "test_decomposed_steps_w_children.json")
    return current_steps


def dfs_find_and_do(task_tree: list[custom_types.Node], task_id: str, action: Callable):
    # find the task label in the current steps using dfs recursively
    # if the task is found, replace it with the decomposed steps
    # if the task is not found, return None
    # here is the code
    for step in task_tree:
        if step["id"] == task_id:
            action(step)
            return
        elif "children" in step:
            dfs_find_and_do(step["children"], task_id, action)
        else:
            continue
    return None


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    # app.run(debug=True)
    import uvicorn

    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=True)
