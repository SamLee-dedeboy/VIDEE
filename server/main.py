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
        "execution_graph": {},
    }
    return {"session_id": session_id}


@app.post("/goal_decomposition/")
async def goal_decomposition(request: Request) -> list[custom_types.Node]:
    request = await request.body()
    request = json.loads(request)
    goal = request["goal"]
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
            open(relative_path("test_primitive_tasks.json"))
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
            decomposed_primitive_tasks, relative_path("test_primitive_tasks.json")
        )
    return decomposed_primitive_tasks


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


@app.post("/primitive_task/compile/")
async def compile_primitive_tasks(request: Request) -> dict:
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    primitive_task_descriptions = request["primitive_tasks"]
    if dev:
        primitive_task_execution_plan = test_execution_plan
    else:
        primitive_task_execution_plan = executor.execution_plan(
            primitive_task_descriptions
        )
    execution_graph = executor.create_graph(primitive_task_execution_plan)
    user_sessions[session_id]["execution_graph"] = execution_graph
    execution_state = executor.init_user_execution_state(
        execution_graph, primitive_task_execution_plan
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
    # update execution state
    user_sessions[session_id]["execution_state"] = executor.make_children_executable(
        execution_graph,
        user_sessions[session_id]["execution_state"],
        execute_node["id"],
    )
    # save_json(current_steps, "test_decomposed_steps_w_children.json")
    return {
        "result": state,
        "execution_state": user_sessions[session_id]["execution_state"],
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

test_execution_plan = [
    {
        "id": "Information Extraction-1",
        "label": "Information Extraction",
        "description": "Automatically identify and extract structured information such as entities from the documents.",
        "explanation": "This task is needed to identify key entities that will form the nodes of the knowledge graph.",
        "state_input_key": "documents",
        "doc_input_keys": ["content"],
        "state_output_key": "entities",
        "parentIds": [],
        "execution": {
            "tool": "prompt_tool",
            "parameters": {
                "name": "entity_extraction",
                "model": "gpt-4o-mini",
                "api_key": api_key,
                "format": "json",
                "prompt_template": [
                    {
                        "role": "system",
                        "content": """
                            ** Context **
                            You are an entity extraction system. The user will give you a piece of text.
                            ** Task **
                            Your task is to extract the entities from the text. 
                            ** Requirements **
                            Reply with the following JSON format: {{ "entities": ["entity1", "entity2", ...] }}
                        """,
                    },
                    {"role": "human", "content": "{content}"},
                ],
            },
        },
    },
    {
        "id": "Information Extraction-2",
        "label": "Information Extraction",
        "description": "Determine the relationships between the extracted entities based on the context of the documents.",
        "explanation": "Understanding the relationships allows us to connect the entities and define the edges of the knowledge graph.",
        "state_input_key": "documents",
        "doc_input_keys": ["content", "entities"],
        "state_output_key": "relationships",
        "parentIds": ["Information Extraction-1"],
        "execution": {
            "tool": "prompt_tool",
            "parameters": {
                "name": "relationship_extraction",
                "model": "gpt-4o-mini",
                "api_key": api_key,
                "format": "json",
                "prompt_template": [
                    {
                        "role": "system",
                        "content": """
                        ** Context **
                        You are a relationship extraction system. The user will give you a piece of text and the entities extracted from it.
                        ** Task **
                        Your task is to extract the relationships between entities from the text. 
                        ** Requirements **
                        Reply with the following JSON format: 
                            {{ "relationships": [
                                {{
                                    "label": (str, label for the relationship), 
                                    "source": (str, entity1),
                                    "target": (str, entity2),
                                    "explanation": (str, explanation of the relationship)
                                }}, 
                                {{
                                    "label": (str, label for the relationship), 
                                    "source": (str, entity1),
                                    "target": (str, entity2),
                                    "explanation": (str, explanation of the relationship)
                                }}, 
                                ...
                                ] 
                            }}
                        """,
                    },
                    {
                        "role": "human",
                        "content": "Content: {content}\n Entities: {entities}",
                    },
                ],
            },
        },
    },
]
