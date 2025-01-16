from typing import Union
from fastapi import FastAPI, Request
import json
import os
from collections import defaultdict
from openai import OpenAI
import AutoGenUtils.query as autogen_utils
from fastapi.middleware.cors import CORSMiddleware
from custom_types import Node
import decomposer as decomposer

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
client = OpenAI(api_key=open("api_key").read(), timeout=10)


@app.get("/test/")
def test():
    return "Hello Task Decomposition"


@app.post("/goal_decomposition/")
async def goal_decomposition(request: Request) -> list[Node]:
    goal = await request.body()
    goal = json.loads(goal)["goal"]
    decomposed_steps = await decomposer.goal_decomposition(goal)
    # decomposed_steps = json.load(
    #     open(relative_path("test_decomposed_steps_w_children.json"))
    # )
    return decomposed_steps


@app.post("/task_decomposition/")
async def task_decomposition(request: Request) -> list[Node]:
    request = await request.body()
    request = json.loads(request)
    task = request["task"]
    current_steps = request["current_steps"]
    # print("get request: \n", task)
    # current_steps = json.load(
    #     open(relative_path("test_decomposed_steps_w_children.json"))
    # )
    # modifies current_steps
    current_steps = await decomposer.task_decomposition(task, current_steps)
    # save_json(current_steps, "test_decomposed_steps_w_children.json")
    return current_steps


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    app.run(debug=True)
