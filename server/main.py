from typing import Union
from fastapi import FastAPI, Request
import json
import os
from collections import defaultdict
from typing import Callable
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


import random
import asyncio

# local packages
import server.custom_types as custom_types
import server.decomposer as decomposer
import server.executor as executor
import server.evaluator as evaluator


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
dataset_path = relative_path("executor/docs.json")
# dataset_path = relative_path("data/papers.json")

dev = True


@app.get("/test/")
def test():
    return "Hello Task Decomposition"


@app.post("/test/stream/")
async def test_stream():
    async def iter_response():  # (1)
        k = 5
        for i in range(k):
            obj = {"id": i, "data": f"Object {i}"}
            yield json.dumps(obj) + "\n"  # Ensure newline separation
            await asyncio.sleep(5)

    return StreamingResponse(iter_response(), media_type="application/json")


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
        "eval_definitions": {
            "complexity": evaluator.complexity_definition,
            "coherence": evaluator.coherence_definition,
            "importance": evaluator.importance_definition,
        },
        "result_evaluators": defaultdict(list),
        "execution_evaluations": defaultdict(list),
    }
    return {"session_id": session_id}


@app.post("/documents/")
async def get_documents(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    # return json.load(open(relative_path("data/papers.json")))
    return json.load(open(dataset_path))


@app.post("/documents/dr/")
async def get_dr(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions

    if "dr_data" in user_sessions[session_id]:
        return user_sessions[session_id]["dr_data"]
    else:
        if False:
            return json.load(open(relative_path("dev_data/test_dr.json")))
        else:
            data = request["data"]
            texts = list(map(lambda x: x["content"], data))

            clusters, cluster_orders, cluster_topics, all_angles = (
                await executor.radial_dr(texts, model=default_model, api_key=api_key)
            )

            for i, datum in enumerate(data):
                data[i]["cluster"] = cluster_orders[clusters[i]]
                data[i]["cluster_label"] = cluster_topics[clusters[i]]
                data[i]["angle"] = all_angles[i]
            save_json(data, relative_path("dev_data/test_dr.json"))

            user_sessions[session_id]["dr_data"] = data
            return data


@app.post("/eval/definitions/")
async def get_eval_definitions(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    return user_sessions[session_id]["eval_definitions"]


@app.post("/eval/definitions/update/")
async def update_eval_definitions(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    updated_eval_definitions = request["eval_definitions"]
    user_sessions[session_id]["eval_definitions"] = updated_eval_definitions
    return "success"


@app.post("/goal_decomposition/mcts/stepped/")
async def goal_decomposition_MCTS_stepped(request: Request):
    request = await request.body()
    request = json.loads(request)
    goal = request["goal"]
    session_id = request["session_id"]
    assert session_id in user_sessions
    # user_sessions[session_id]["goal"] = goal
    semantic_tasks = request["semantic_tasks"] if "semantic_tasks" in request else None
    eval_definitions = user_sessions[session_id]["eval_definitions"]
    eval_few_shot_examples = (
        request["eval_few_shot_examples"] if "eval_few_shot_examples" in request else []
    )
    select_strategy_arg = (
        request["select_strategy"] if "select_strategy" in request else None
    )
    next_selection = (
        custom_types.MCT_Node.model_validate(request["next_expansion"])
        if "next_expansion" in request
        else None
    )
    if semantic_tasks is None or semantic_tasks == []:
        user_root = decomposer.init_MCTS()
        node_dict = {user_root.MCT_id: user_root}
    else:
        node_dict = {
            t["MCT_id"]: custom_types.MCT_Node.model_validate(t) for t in semantic_tasks
        }
        user_root = node_dict["-1"]

    # node_dict = decomposer.collect_MCT_node_dict(user_root)

    async def iter_response(
        root,
        node_dict,
        goal,
        next_selection,
        eval_definitions,
        eval_few_shot_examples,
        select_strategy_arg,
    ):  # (1)
        async for (
            new_root,
            node_dict,
            next_selection,
            max_value_path,
        ) in decomposer.stream_MCTS(
            root,
            node_dict,
            goal,
            next_selection=next_selection,
            eval_definitions=eval_definitions,
            eval_few_shot_examples=eval_few_shot_examples,
            model=default_model,
            api_key=api_key,
            select_strategy_arg=select_strategy_arg,
        ):
            if next_selection is None:
                break
            try:
                root = new_root
                save_json(
                    {
                        "node_dict": {
                            k: v.model_dump(mode="json") for k, v in node_dict.items()
                        },
                        "next_node": next_selection.model_dump(mode="json"),
                        "max_value_path": max_value_path,
                    },
                    relative_path("dev_data/test_mcts_root.json"),
                )
                yield json.dumps(
                    {
                        "node_dict": {
                            k: v.model_dump(mode="json") for k, v in node_dict.items()
                        },
                        "next_node": next_selection.model_dump(mode="json"),
                        "max_value_path": max_value_path,
                    }
                ) + "\n"
            except Exception as exception:
                print(f"Error inside iter_response loop: {exception}")
                pass

    try:
        return StreamingResponse(
            iter_response(
                root=user_root,
                node_dict=node_dict,
                goal=goal,
                next_selection=next_selection,
                eval_definitions=eval_definitions,
                eval_few_shot_examples=eval_few_shot_examples,
                select_strategy_arg=select_strategy_arg,
            ),
            media_type="application/json",
        )
    except Exception as e:
        print(f"Error in iter_response: {e}")


@app.post("/goal_decomposition/mcts/regenerate/")
async def goal_decomposition_MCTS_regenerate(request: Request):
    request = await request.body()
    request = json.loads(request)
    goal = request["goal"]
    session_id = request["session_id"]
    assert session_id in user_sessions
    # user_sessions[session_id]["goal"] = goal
    semantic_tasks = request["semantic_tasks"] if "semantic_tasks" in request else None
    target_task = (
        custom_types.MCT_Node.model_validate(request["target_task"])
        if "target_task" in request
        else None
    )
    eval_definitions = user_sessions[session_id]["eval_definitions"]
    eval_few_shot_examples = (
        request["eval_few_shot_examples"] if "eval_few_shot_examples" in request else []
    )
    if semantic_tasks is None or semantic_tasks == []:
        user_root = decomposer.init_MCTS()
        node_dict = {user_root.MCT_id: user_root}
    else:
        node_dict = {
            t["MCT_id"]: custom_types.MCT_Node.model_validate(t) for t in semantic_tasks
        }
        user_root = node_dict["-1"]
    new_root, node_dict, next_selection, max_value_path = (
        await decomposer.MCTS_regenerate(
            user_root,
            target_task,
            node_dict,
            goal,
            model=default_model,
            api_key=api_key,
            eval_definitions=eval_definitions,
            eval_few_shot_examples=eval_few_shot_examples,
        )
    )
    try:
        root = new_root
        save_json(
            {
                "node_dict": {
                    k: v.model_dump(mode="json") for k, v in node_dict.items()
                },
                "next_node": next_selection.model_dump(mode="json"),
                "max_value_path": max_value_path,
            },
            relative_path("dev_data/test_mcts_root.json"),
        )
        return {
            "node_dict": {k: v.model_dump(mode="json") for k, v in node_dict.items()},
            "next_node": next_selection.model_dump(mode="json"),
            "max_value_path": max_value_path,
        }

    except Exception as exception:
        print(f"Error inside iter_response loop: {exception}")
        pass


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
async def semantic_task_decomposition_to_primitive_task(request: Request):
    request = await request.body()
    request = json.loads(request)
    target_task = request["task"] if "task" in request else None
    semantic_tasks = request["semantic_tasks"]
    semantic_tasks = [custom_types.Node.model_validate(t) for t in semantic_tasks]
    semantic_tasks = list(
        filter(lambda t: t.label != "END" and t.id != "root", semantic_tasks)
    )
    primitive_task_list = json.load(
        open(relative_path("decomposer/primitive_task_defs.json"))
    )
    return await decomposer.one_shot_decomposition_to_primitive_task(
        semantic_tasks=semantic_tasks,
        primitive_task_list=primitive_task_list,
        model=default_model,
        api_key=api_key,
    )

    async def iter_response(semantic_tasks, primitive_task_list):  # (1)
        async for (
            semantic_task,
            primitive_tasks,
        ) in decomposer.stream_decomposition_to_primitive_tasks(
            semantic_tasks=semantic_tasks,
            primitive_task_list=primitive_task_list,
            model=default_model,
            api_key=api_key,
        ):
            try:
                save_json(
                    {
                        "semantic_task": semantic_task.model_dump(mode="json"),
                        "primitive_tasks": primitive_tasks,
                    },
                    relative_path(
                        f"dev_data/test_decomposition_to_primitive_tasks/{semantic_task.label}.json"
                    ),
                )
                yield json.dumps(
                    {
                        "semantic_task": semantic_task.model_dump(mode="json"),
                        "primitive_tasks": primitive_tasks,
                    }
                ) + "\n"
            except Exception as exception:
                print(f"Error inside iter_response loop: {exception}")
                pass

    if target_task is None:
        try:
            return StreamingResponse(
                iter_response(
                    semantic_tasks=semantic_tasks,
                    primitive_task_list=primitive_task_list,
                ),
                media_type="application/json",
            )
        except Exception as e:
            print(f"Error in iter_response: {e}")
    else:
        return decomposer.regenerate_decomposition_to_primitive_task(
            target_task=target_task,
            semantic_tasks=semantic_tasks,
            primitive_task_list=primitive_task_list,
            model=default_model,
            api_key=api_key,
        )
    pass


@app.get("/primitive_task/list/")
async def get_primitive_list():
    primitive_task_list = json.load(
        open(relative_path("decomposer/primitive_task_defs.json"))
    )
    return primitive_task_list


# @app.post("/primitive_task/update/")
# async def update_primitive_tasks(request: Request) -> dict:
#     request = await request.body()
#     request = json.loads(request)
#     session_id = request["session_id"]
#     assert session_id in user_sessions
#     primitive_tasks = request["primitive_tasks"]
#     user_sessions[session_id]["primitive_tasks"] = primitive_tasks
#     return {"status": "success"}


@app.post("/primitive_task/compile/")
async def compile_primitive_tasks(request: Request) -> dict:
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    primitive_task_descriptions = request["primitive_tasks"]
    compile_target = request["compile_target"] if "compile_target" in request else None
    skip_IO = request["skip_IO"] if "skip_IO" in request else False
    skip_parameters = request["skip_parameters"] if "skip_parameters" in request else False
    root_description = next(
        (x for x in primitive_task_descriptions if x["id"] == "-1"), None
    )

    primitive_task_descriptions = list(
        filter(lambda x: x["id"] != "-1", primitive_task_descriptions)
    )
    if dev:
        primitive_task_execution_plan = json.load(
            open(relative_path("dev_data/test_execution_plan.json"))
        )
        primitive_task_execution_plan = primitive_task_execution_plan[1:]
    else:
        primitive_task_execution_plan = await executor.execution_plan(
            primitive_task_descriptions,
            compile_target=compile_target,
            skip_IO=skip_IO,
            skip_parameters=skip_parameters,
            model=default_model,
            api_key=api_key,
        )
    # retain execution history if we are compiling a task target
    should_preserve_history = compile_target and (skip_IO or skip_parameters)
    old_checkpointer = user_sessions[session_id]['checkpointer'] if should_preserve_history else None
    execution_graph, checkpointer = executor.create_graph(
        primitive_task_execution_plan, checkpointer=old_checkpointer
    )
    user_sessions[session_id]["execution_graph"] = execution_graph
    user_sessions[session_id]["checkpointer"] = checkpointer
    execution_state = executor.init_user_execution_state(
        execution_graph,
        primitive_task_execution_plan,
    )

    if should_preserve_history and session_id in user_sessions:
        old_execution_state = user_sessions[session_id]["execution_state"]
        old_execution_results = user_sessions[session_id]["execution_results"]

        # Function to recursively copy executed state and results
        def copy_executed_history(node_id, stop_at_id):
            if node_id == stop_at_id:
                return

            if node_id in old_execution_state and old_execution_state[node_id].get("executed", False) == True:
                # Copy execution state
                execution_state[node_id]["executed"] = True
                execution_state[node_id]["executable"] = old_execution_state[node_id].get("executable", True)

                # Make children executable if they exist in the new graph
                for child_id in execution_state[node_id].get("childrenIds", []):
                    if child_id in execution_state:
                        execution_state[child_id]["executable"] = True

                # Copy execution results
                if node_id in old_execution_results:
                    user_sessions[session_id]["execution_results"][node_id] = old_execution_results[node_id]

                # Process children recursively
                for child_id in execution_state[node_id].get("childrenIds", []):
                    copy_executed_history(child_id, stop_at_id)

        # Find root nodes (nodes with no parents) and start copying
        root_nodes = [node_id for node_id, node in execution_state.items()
                     if not node.get("parentIds") or len(node.get("parentIds", [])) == 0]
        # ideally there should be only one root node
        copy_executed_history(root_nodes[0], compile_target)

    user_sessions[session_id]["execution_state"] = execution_state
    primitive_task_execution_plan.insert(0, root_description)
    save_json(
        primitive_task_execution_plan,
        relative_path("dev_data/test_execution_plan.json"),
    )
    return {
        "primitive_tasks": primitive_task_execution_plan,
        "execution_state": execution_state,
    }


@app.post("/primitive_task/update/")
async def update_primitive_tasks(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    primitive_task_execution_plan = request["primitive_tasks"]
    root_task = next(
        (x for x in primitive_task_execution_plan if x["id"] == "-1"), None
    )
    primitive_task_execution_plan = list(
        filter(lambda x: x["id"] != "-1", primitive_task_execution_plan)
    )
    save_json(
        primitive_task_execution_plan,
        relative_path("dev_data/test_execution_plan_updated.json"),
    )
    checkpointer = user_sessions[session_id]["checkpointer"]
    execution_graph, _ = executor.create_graph(
        primitive_task_execution_plan,
        checkpointer=checkpointer,
    )
    user_sessions[session_id]["execution_graph"] = execution_graph
    primitive_task_execution_plan.insert(0, root_task)
    return {
        "primitive_tasks": primitive_task_execution_plan,
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
    initial_state = {"documents": json.load(open(dataset_path))}

    last_state = executor.find_last_state(execution_graph, execute_node, thread_config)
    last_state = last_state if last_state is not None else initial_state
    state = executor.execute_node(
        execution_graph,
        thread_config,
        execute_node,
        parent_version,
        state=last_state,
    )
    # update execution state by adding the executed node as "executed" and updating its children "executable" states
    user_sessions[session_id]["execution_state"] = executor.update_execution_state(
        user_sessions[session_id]["execution_state"],
        execute_node,
    )
    user_sessions[session_id]["execution_results"][execute_node] = state
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
    result = user_sessions[session_id]["execution_results"][task_id]
    # if dev:
    #     result = json.load(open(relative_path("dev_data/test_execution_result.json")))
    # else:
    #     result = user_sessions[session_id]["execution_results"][task_id]

    return {
        "result": result,
    }


@app.post("/primitive_task/evaluators/recommend/")
async def recommend_evaluators(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions

    tasks = request["tasks"]
    goal = request["goal"]
    evaluator_task_description_pairs = await executor.generate_evaluator_descriptions(
        goal, tasks, model=default_model, api_key=api_key
    )
    evaluator_specs = await executor.create_evaluator_specs(
        evaluator_task_description_pairs, model=default_model, api_key=api_key
    )
    for evaluator_spec, (task, description) in zip(
        evaluator_specs, evaluator_task_description_pairs
    ):
        evaluator_spec["task"] = task["id"]
        evaluator_spec["recommendation"] = True
    return {"result": evaluator_specs}


@app.post("/primitive_task/evaluators/add/")
async def add_evaluators(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions

    task = request["task"]
    user_description = request["description"]

    evaluator_spec = await executor.create_evaluator_spec(
        task, user_description, default_model, api_key
    )
    evaluator_spec["task"] = task["id"]
    return {"result": evaluator_spec}


@app.post("/primitive_task/evaluators/run/")
async def run_evaluators(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions

    evaluator_spec = request["evaluator"]
    evaluator_exec = await executor.create_evaluator_exec(evaluator_spec)
    task_id = evaluator_spec["task"]
    execution_result = user_sessions[session_id]["execution_results"][task_id]

    evaluation_result = evaluator_exec.invoke(
        execution_result, config={"configurable": {"thread_id": session_id}}
    )
    user_sessions[session_id]["execution_evaluations"][task_id].append(
        {
            "name": evaluator_spec["name"],
            "result": evaluation_result,
            "possible_scores": evaluator_spec["possible_scores"],
        }
    )
    return {"results": user_sessions[session_id]["execution_evaluations"][task_id]}


@app.post("/primitive_task/evaluators/result/")
async def fetch_primitive_task_result(request: Request):
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    task_id = request["task_id"]
    evaluator_name = request["evaluator_name"]
    all_results = user_sessions[session_id]["execution_evaluations"][task_id]
    evaluator_result = next(
        filter(lambda x: x["name"] == evaluator_name, all_results), None
    )
    return {
        "result": evaluator_result,
    }


@app.get("/dev/semantic_task/plan/")
def get_dev_plan():
    return json.load(open(relative_path("dev_data/test_mcts_root.json")))


@app.post("/semantic_task/decomposition_to_primitive_tasks/dev/")
def dev_convert():
    return json.load(open(relative_path("dev_data/test_execution_plan.json")))


@app.post("/primitive_task/compile/dev/")
async def compile_primitive_tasks(request: Request) -> dict:
    request = await request.body()
    request = json.loads(request)
    session_id = request["session_id"]
    assert session_id in user_sessions
    compile_target = request["compile_target"] if "compile_target" in request else None
    primitive_task_execution_plan = json.load(
        open(relative_path("dev_data/test_execution_plan.json"))
    )
    root_description = next(
        (x for x in primitive_task_execution_plan if x["id"] == "-1"), None
    )

    primitive_task_execution_plan = list(
        filter(lambda x: x["id"] != "-1", primitive_task_execution_plan)
    )
    execution_graph, checkpointer = executor.create_graph(
        primitive_task_execution_plan, checkpointer=None
    )
    user_sessions[session_id]["execution_graph"] = execution_graph
    user_sessions[session_id]["checkpointer"] = checkpointer
    execution_state = executor.init_user_execution_state(
        execution_graph,
        primitive_task_execution_plan,
    )
    user_sessions[session_id]["execution_state"] = execution_state
    primitive_task_execution_plan.insert(0, root_description)
    return {
        "primitive_tasks": primitive_task_execution_plan,
        "execution_state": execution_state,
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

# @app.post("/goal_decomposition/beam_search/stepped/")
# async def goal_decomposition_beam_search_stepped(request: Request):
#     request = await request.body()
#     request = json.loads(request)
#     goal = request["goal"]
#     session_id = request["session_id"]
#     assert session_id in user_sessions
#     user_sessions[session_id]["goal"] = goal
#     user_steps = request["user_steps"]
#     print("user_steps", user_steps)
#     k, n = 2, 2
#     if False:
#         decomposed_steps = json.load(
#             open(relative_path("dev_data/test_decomposed_steps_w_children.json"))
#         )
#         user_sessions[session_id]["semantic_tasks"] = decomposed_steps
#         return decomposed_steps
#     else:

#         async def iter_response(candidate_steps):  # (1)
#             if len(candidate_steps) == 0:
#                 candidate_steps = await decomposer.goal_decode_n_samples(
#                     goal, [], default_model, api_key, n=n
#                 )
#                 yield json.dumps({"semantic_tasks": candidate_steps}) + "\n"
#             async for steps in decomposer.stream_goal_beam_search(
#                 goal, candidate_steps, default_model, api_key, k=k, n=n
#             ):
#                 candidate_steps = steps
#                 save_json(
#                     candidate_steps,
#                     relative_path("dev_data/test_beam_search_candidate_steps.json"),
#                 )
#                 yield json.dumps({"semantic_tasks": candidate_steps}) + "\n"

#         return StreamingResponse(
#             iter_response(user_steps), media_type="application/json"
#         )

# @app.post("/goal_decomposition/beam_search/stepped/")
# async def goal_decomposition_beam_search_stepped(request: Request):
#     request = await request.body()
#     request = json.loads(request)
#     goal = request["goal"]
#     session_id = request["session_id"]
#     assert session_id in user_sessions
#     user_sessions[session_id]["goal"] = goal
#     user_steps = request["user_steps"]
#     print("user_steps", user_steps)
#     k, n = 2, 2
#     if False:
#         decomposed_steps = json.load(
#             open(relative_path("dev_data/test_decomposed_steps_w_children.json"))
#         )
#         user_sessions[session_id]["semantic_tasks"] = decomposed_steps
#         return decomposed_steps
#     else:

#         async def iter_response(candidate_steps):  # (1)
#             if len(candidate_steps) == 0:
#                 candidate_steps = await decomposer.goal_decode_n_samples(
#                     goal, [], default_model, api_key, n=n
#                 )
#                 yield json.dumps({"semantic_tasks": candidate_steps}) + "\n"
#             async for steps in decomposer.stream_goal_beam_search(
#                 goal, candidate_steps, default_model, api_key, k=k, n=n
#             ):
#                 candidate_steps = steps
#                 save_json(
#                     candidate_steps,
#                     relative_path("dev_data/test_beam_search_candidate_steps.json"),
#                 )
#                 yield json.dumps({"semantic_tasks": candidate_steps}) + "\n"

#         return StreamingResponse(
#             iter_response(user_steps), media_type="application/json"
#         )