import server.executor.tools as custom_tools
from .langgraph_utils import get_input_func, reduce_func
from langchain_core.runnables import RunnableAssign, RunnableLambda
from server.AutoGenUtils import query
from langgraph.graph import END, START, StateGraph, MessagesState
from server.custom_types import BaseStateSchema
from langgraph.checkpoint.memory import MemorySaver
from tqdm.asyncio import tqdm_asyncio


async def generate_evaluator_descriptions(goal, tasks, model, api_key):
    nested_evaluators = await query.run_evaluator_generation_agent(
        goal, tasks, model, api_key
    )
    recommendation_pairs = []
    for task, evaluators in zip(tasks, nested_evaluators):
        for evaluator in evaluators:
            recommendation_pairs.append((task, evaluator["description"]))
    return recommendation_pairs


async def create_evaluator_specs(evaluator_description_pairs, model, api_key):
    tasks = [
        create_evaluator_spec(task, description, model, api_key)
        for task, description in evaluator_description_pairs
    ]
    results = await tqdm_asyncio.gather(*tasks, desc="generating evaluator specs")
    return results


def evaluator_reduce_func(combined, state_input_key, state_output_key):
    outputs = combined[state_output_key]  # "summaries"
    documents = combined[state_input_key]  # "documents"
    return {
        "documents": [
            {**doc, state_output_key: output} for doc, output in zip(documents, outputs)
        ]
    }


async def create_evaluator_exec(evaluator_spec):
    # evaluator_node = create_llm_evaluator_chain(
    #     evaluator_spec, custom_reduce_func=evaluator_reduce_func
    # )
    evaluator_node = create_llm_evaluator_chain(evaluator_spec)
    graph = StateGraph(BaseStateSchema)
    graph.add_node(evaluator_spec["name"], evaluator_node)
    graph.add_edge(START, evaluator_spec["name"])
    app = graph.compile(checkpointer=MemorySaver())
    return app


async def create_evaluator_spec(task, user_description, model, api_key):
    evaluator_spec = await evaluator_for_task(task, user_description, model, api_key)
    return evaluator_spec
    # evaluator_node = create_llm_evaluator_chain(evaluator_spec)
    # graph = StateGraph(BaseStateSchema)
    # graph.add_node(evaluator_spec["name"], evaluator_node)
    # graph.add_edge(START, evaluator_spec["name"])
    # app = graph.compile(checkpointer=MemorySaver())
    # return app, evaluator_spec
    # execute with this
    final_state = app.invoke(
        test_execution_result,
        config={"configurable": {"thread_id": 42}},
    )


async def evaluator_for_task(task, user_description: str, model: str, api_key: str):
    evaluator = await query.run_result_evaluator_generation_agent(
        task, user_description, model, api_key
    )
    input_keys = task["doc_input_keys"] + [
        task["state_output_key"]
    ]  # consider using another agent?
    output_key = evaluator["name"] + "_output"

    # evaluator["prompt_template"]["JSON_format"] = (
    #     evaluator["prompt_template"]["JSON_format"]
    #     .replace("{", "{{")
    #     .replace("}", "}}")
    #     .replace("'", '"')
    # )
    json_format_str = """Reply with the following JSON format:
        {{{{
            {output_key}: a single string (one of the possible scores)
        }}}}
    """.format(
        output_key=output_key,
        possible_scores=evaluator["prompt_template"]["Possible Scores"],
    )
    prompt_template = [
        {
            "role": "system",
            "content": """
                ** Context **
                {prompt_context}
                ** Task **
                {prompt_task}
                ** Requirements **
                Generate one of the following scores for each document:
                Possible Scores: {prompt_requirements}
                {prompt_output_format}
                """.format(
                prompt_context=evaluator["prompt_template"]["Context"],
                prompt_task=evaluator["prompt_template"]["Task"],
                prompt_requirements=evaluator["prompt_template"]["Possible Scores"],
                # prompt_output_format=evaluator["prompt_template"]["JSON_format"],
                prompt_output_format=json_format_str,
            ),
        },
        {
            "role": "human",
            "content": "\n".join([f"{key}: {{{key}}}" for key in input_keys]),
        },
    ]

    full_evaluator_specification = {
        "name": evaluator["name"],
        "definition": evaluator["definition"],
        "state_input_key": task["state_input_key"],
        "doc_input_keys": input_keys,
        "state_output_key": output_key,
        "tool": "prompt_tool",
        "parameters": {
            "name": evaluator["name"] + "-prompt-template",
            "model": model,
            "api_key": api_key,
            "format": "json",
            "prompt_template": prompt_template,
        },
        "possible_scores": evaluator["prompt_template"]["Possible Scores"],
    }
    return full_evaluator_specification


def create_llm_evaluator_chain(
    evaluator, custom_get_input_func=None, custom_reduce_func=None
):
    execution_chain = convert_spec_to_chain(evaluator)
    state_input_key = evaluator["state_input_key"]
    doc_input_keys = evaluator["doc_input_keys"]
    state_output_key = evaluator["state_output_key"]

    # how to get input
    if custom_get_input_func is None:
        get_input = lambda state: get_input_func(state, state_input_key, doc_input_keys)
    else:
        get_input = lambda state: custom_get_input_func(
            state, state_input_key, doc_input_keys
        )
    # create the map-reduce chain
    map = RunnableAssign(
        {
            state_output_key: get_input
            | RunnableLambda(func=execution_chain.batch, afunc=execution_chain.abatch)
        }
    )
    if custom_reduce_func is None:
        reduce = lambda combined: reduce_func(
            combined, state_input_key, state_output_key
        )
    else:
        reduce = lambda state: custom_reduce_func(
            state, state_input_key, state_output_key
        )

    return map | reduce


def convert_spec_to_chain(spec):
    if spec["tool"] == "prompt_tool":
        return custom_tools.prompt_tool(
            spec["parameters"]["name"],
            custom_tools.parse_template(spec["parameters"]["prompt_template"]),
            spec["parameters"]["model"],
            spec["parameters"]["api_key"],
            spec["parameters"]["format"],
        )
    else:
        raise ValueError(f"Unknown execution type: {spec}")
