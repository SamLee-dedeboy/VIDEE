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
import random

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
user_sessions = {}

dev = True


@app.get("/test/")
def test():
    return "Hello Task Decomposition"


@app.post("/session/create/")
async def create_session(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    user_sessions[session_id] = {
        "goal": "",
        "semantic_tasks": [],
        "primitive_tasks": [],
        "execution_graph": {},
        "execution_state": {},
        "execution_results": {},
    }
    return {"session_id": session_id}


@app.post("/documents/")
async def get_documents(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    return json.load(open(relative_path("executor/docs.json")))


@app.post("/goal_decomposition/")
async def goal_decomposition(request: Request) -> list[custom_types.Node]:
    request = await request.body()
    request = json.loads(request)
    goal = request["goal"]
    session_id = request["session_id"]
    assert session_id in user_sessions
    user_sessions[session_id]["goal"] = goal
    if dev:
        decomposed_steps = json.load(
            open(relative_path("dev_data/test_decomposed_steps_w_children.json"))
        )
    else:
        decomposed_steps = await decomposer.goal_decomposition(
            goal, model=default_model, api_key=api_key
        )
        save_json(
            decomposed_steps,
            relative_path("dev_data/test_decomposed_steps_w_children.json"),
        )
    user_sessions[session_id]["semantic_tasks"] = decomposed_steps
    return decomposed_steps


@app.post("/semantic_task/update/")
async def update_semantic_tasks(request: Request) -> dict:
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    semantic_tasks = request["semantic_tasks"]
    user_sessions[session_id]["semantic_tasks"] = semantic_tasks
    return {"status": "success"}


@app.post("/semantic_task/task_decomposition/")
async def task_decomposition(request: Request) -> list[custom_types.Node]:
    request = await request.body()
    request = json.loads(request)
    task = request["task"]
    current_steps = request["current_steps"]
    if False:
        current_steps = json.load(
            open(relative_path("dev_data/test_decomposed_steps_w_children.json"))
        )
    else:
        # modifies current_steps
        current_steps = await decomposer.task_decomposition(
            task, current_steps, model=default_model, api_key=api_key
        )
        save_json(
            current_steps,
            relative_path("dev_data/test_decomposed_steps_w_children.json"),
        )
    return current_steps


@app.post("/semantic_task/decomposition_to_primitive_tasks/")
async def task_decomposition(request: Request) -> list:
    request = await request.body()
    request = json.loads(request)
    task = request["task"]
    current_steps = request["current_steps"]
    primitive_task_list = json.load(
        open(relative_path("decomposer/primitive_task_defs.json"))
    )
    if dev:
        decomposed_primitive_tasks = json.load(
            open(relative_path("dev_data/test_primitive_tasks.json"))
        )
    else:
        decomposed_primitive_tasks = await decomposer.decomposition_to_primitive_task(
            task,
            current_steps,
            primitive_task_list,
            model=default_model,
            api_key=api_key,
        )
        save_json(
            decomposed_primitive_tasks,
            relative_path("dev_data/test_primitive_tasks.json"),
        )
    return decomposed_primitive_tasks


@app.post("/primitive_task/update/")
async def update_primitive_tasks(request: Request) -> dict:
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    primitive_tasks = request["primitive_tasks"]
    user_sessions[session_id]["primitive_tasks"] = primitive_tasks
    return {"status": "success"}


@app.post("/primitive_task/compile/")
async def compile_primitive_tasks(request: Request) -> dict:
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    primitive_task_descriptions = request["primitive_tasks"]
    primitive_task_execution_plan = await executor.execution_plan(
        primitive_task_descriptions,
        model=default_model,
        api_key=api_key,
    )
    execution_graph = executor.create_graph(primitive_task_execution_plan)
    user_sessions[session_id]["execution_graph"] = execution_graph
    execution_state = executor.init_user_execution_state(
        execution_graph,
        primitive_task_execution_plan,
    )
    user_sessions[session_id]["execution_state"] = execution_state
    return {
        "primitive_tasks": primitive_task_execution_plan,
        "execution_state": execution_state,
    }


@app.post("/primitive_task/execute/")
async def execute_primitive_tasks(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    execution_graph = user_sessions[session_id]["execution_graph"]
    execute_node = request["execute_node"]
    parent_version = (
        request["parent_version"] if "parent_version" in request else None
    )  # the parent version that the node is executed from
    thread_config = {"configurable": {"thread_id": 42}}
    initial_state = {"documents": json.load(open(relative_path("executor/docs.json")))}
    state = executor.execute_node(
        execution_graph,
        thread_config,
        execute_node,
        parent_version,
        initial_state=initial_state,
    )
    # update execution state by adding the executed node as "executed" and updating its children "executable" states
    user_sessions[session_id]["execution_state"] = executor.update_execution_state(
        user_sessions[session_id]["execution_state"],
        execute_node["id"],
    )
    user_sessions[session_id]["execution_results"][execute_node["id"]] = state
    save_json(state, relative_path("dev_data/test_execution_result.json"))
    # save_json(current_steps, "test_decomposed_steps_w_children.json")
    return {
        "execution_state": user_sessions[session_id]["execution_state"],
    }


@app.post("/primitive_task/result/")
async def fetch_primitive_task_result(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    task_id = request["task_id"]
    if dev:
        result = json.load(open(relative_path("dev_data/test_execution_result.json")))
    else:
        result = user_sessions[session_id]["execution_results"][task_id]

    return {
        "result": result,
    }


def dfs_find_and_do(task_tree: list[custom_types.Node], task_id: str, action: Callable):
    # find the task label in the current steps using dfs recursively
    # if the task is found, replace it with the decomposed steps
    # if the task is not found, return None
    # here is the code
    for step in task_tree:
        if step["id"] == task_id:
            action(step)
            return
        elif "sub_tasks" in step:
            dfs_find_and_do(step["sub_tasks"], task_id, action)
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
