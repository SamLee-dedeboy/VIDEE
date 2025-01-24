import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import (
    RunnableConfig,
    RunnableLambda,
    RunnablePassthrough,
    RunnableAssign,
)

from server.custom_types import ElementaryTaskDef, BaseStateSchema
import server.executor.tools as custom_tools


def create_nodes(steps: list[ElementaryTaskDef]):
    return [create_node(step) for step in steps]


def create_graph(steps: list[ElementaryTaskDef]):
    graph = StateGraph(BaseStateSchema)
    nodes = create_nodes(steps)
    # create an empty node as root to signal the start of the graph
    root = create_root()
    graph.add_node("root", root)
    graph.add_edge(START, "root")

    # add nodes and edges to the graph
    for step, node in zip(steps, nodes):
        graph.add_node(step["id"], node)
        if step["parentIds"] == []:
            graph.add_edge("root", step["id"])
        else:
            for parent_id in step["parentIds"]:
                graph.add_edge(parent_id, step["id"])
    return graph


def execute_node(node_id):
    pass


# create an execution chain for the step
# first, specify how to get the input (map)
# then, specify the function to execute on the input (map)
# finally, specify how to format the output (reduce)
def create_node(step, custom_get_input_func=None, custom_reduce_func=None):
    execution_chain = convert_spec_to_chain(step["execution"])
    state_input_key = step["state_input_key"]
    doc_input_keys = step["doc_input_keys"]
    state_output_key = step["state_output_key"]
    # how to get input
    if custom_get_input_func is None:
        get_input = lambda state: get_input_func(state, state_input_key, doc_input_keys)
    else:
        get_input = custom_get_input_func
    # how to produce output
    if custom_reduce_func is None:
        reduce = lambda combined: reduce_func(
            combined, state_input_key, state_output_key
        )
    else:
        reduce = custom_reduce_func
    # create the map-reduce chain
    map = RunnableAssign(
        {
            state_output_key: get_input
            | RunnableLambda(func=execution_chain.batch, afunc=execution_chain.abatch)
        }
    )
    map_reduce_chain = map | reduce
    return map_reduce_chain


# an empty node that is the root of the graph
def create_root():
    return RunnableLambda(func=lambda x: x)


# a common get input function
def get_input_func(state, state_input_key: str, doc_input_keys: list[str]):
    docs = state[
        state_input_key
    ]  # how to get the list of docs from the state (e.g. state["documents"])
    return [
        {key: doc[key] for key in doc_input_keys if key in doc} for doc in docs
    ]  # how to get the input field from a doc (e.g. doc["content"])


# a common reduce function
def reduce_func(combined: dict, state_input_key: str, state_output_key: str):
    outputs = combined[state_output_key]  # "summaries"
    documents = combined[state_input_key]  # "documents"
    return {
        "documents": [
            {**doc, **{k: v for k, v in output.items()}}
            for doc, output in zip(documents, outputs)
        ]
    }


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
