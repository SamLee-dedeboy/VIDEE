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
from langgraph.types import Command, interrupt
from collections import defaultdict


from server.custom_types import (
    ElementaryTaskExecution,
    ElementaryTaskDescription,
    UserExecutionState,
    BaseStateSchema,
)
import server.executor.tools as custom_tools


def init_user_execution_state(
    execution_graph, execution_plan
) -> dict[str, UserExecutionState]:
    # collect dictionaries to be used later
    node_dict = {node["id"]: node for node in execution_plan}
    children_dict = defaultdict(list)
    for node in execution_plan:
        node_dict[node["id"]] = node
        for parent_id in node["parentIds"]:
            children_dict[parent_id].append(node["id"])

    # create the user execution state
    user_execution_state = {}
    first_node = True
    for node in execution_graph.get_graph().nodes:
        if node == "__start__":
            continue
        if node.endswith("_evaluation"):
            continue
        user_execution_state[node] = {
            "executable": first_node,
            "childrenIds": children_dict[node],
            "parentIds": node_dict[node]["parentIds"],
        }
        first_node = False
    return user_execution_state


def make_children_executable(execution_graph, user_execution_state, node_id):
    for _node in execution_graph.get_graph().nodes:
        if _node == node_id:
            children_ids = user_execution_state[_node]["childrenIds"]
            for child_id in children_ids:
                user_execution_state[child_id]["executable"] = True
            break
    return user_execution_state


def execution_plan(
    steps: list[ElementaryTaskDescription],
) -> list[ElementaryTaskExecution]:
    plan = []
    for step in steps:
        plan.append(
            {
                "id": step["id"],
                "label": step["label"],
                "description": step["definition"],
                "explanation": step["explanation"],
                "parentIds": step["parentIds"],
                "state_input_key": step["state_input_key"],  # to be generated
                "doc_input_keys": step["doc_input_key"],  # to be generated
                "state_output_key": step["state_output_key"],  # to be generated
                "execution": step["execution"],  # to be generated
            }
        )
    return plan


def create_nodes(steps: list[ElementaryTaskExecution]):
    return [create_node(step) for step in steps]


def create_graph(steps: list[ElementaryTaskExecution]):
    graph = StateGraph(BaseStateSchema)
    nodes = create_nodes(steps)
    # create an empty node as root to signal the start of the graph
    # root = create_root()
    # graph.add_node("root", root)
    # graph.add_edge(START, "root")

    # add nodes to the graph
    # children_dict = dict()
    # children_dict["root"] = []
    for step, node in zip(steps, nodes):
        # children_dict[step["id"]] = []
        graph.add_node(step["id"], node)
        graph.add_node(f"{step['id']}_evaluation", human_approval)
        graph.add_edge(step["id"], f"{step['id']}_evaluation")

        if step["parentIds"] == []:
            # children_dict["root"].append(step["id"])
            graph.add_edge(START, step["id"])
        else:
            for parent_id in step["parentIds"]:
                # children_dict[parent_id].append(step["id"])
                graph.add_edge(f"{parent_id}_evaluation", step["id"])
                # graph.add_edge(f"{parent_id}", step["id"])
    # add edges
    # for parent_id, children in children_dict.items():
    #     if parent_id == "root":
    #         for child in children:
    #             graph.add_edge("root", child)
    #     else:
    #         graph.add_node(
    #             f"{parent_id}_evaluation", human_approval_node(parent_id, children)
    #         )
    #         graph.add_edge(parent_id, f"{parent_id}_evaluation")
    #         graph.add_edge(f"{parent_id}_evaluation", parent_id)
    #         for child in children:
    #             graph.add_edge(f"{parent_id}_evaluation", child)
    return graph.compile(checkpointer=MemorySaver())


def human_approval(state):
    interrupt("Please provide feedback:")
    return state


# def human_approval_node(parent_id, children_id):
#     def human_approval(state):
#         print("---human_feedback---", state["documents"][0].keys())
#         response = interrupt("Please provide feedback:")
#         approved = response["approved"]
#         print("approved:", approved)
#         print("children_id:", children_id)
#         print("parent_id:", parent_id)
#         if approved:
#             print("going to children")
#             return Command(goto=children_id)
#         else:
#             print("going to parent")
#             return Command(goto=parent_id)

#     return human_approval


def get_node_config(app, thread_config, node_id, execution_version=None):
    state_history = list(
        reversed([step for step in app.get_state_history(thread_config)])
    )
    node_configs = [
        step.config for step in state_history if step.next == f"{node_id}_evaluation"
    ]
    if len(node_configs) == 0:
        return None
    if execution_version is None:
        return node_configs[-1]
    else:
        return node_configs[execution_version]


def execute_node(
    app, thread_config, node_id, execution_version=None, initial_state=None
):
    # if this is the first node executed in the graph
    # then we need to invoke with the initial state
    if len(list(app.get_state_history(thread_config))) == 0:
        state = app.invoke(initial_state, config=thread_config)
        return state

    # if this is not the first node executed in the graph
    # check if this node is executed before
    node_config = get_node_config(app, thread_config, node_id, execution_version)
    if node_config is None:  # first time executing this node
        state = app.invoke(Command(resume=True), config=thread_config)
    else:  # if this node is executed before
        state = app.invoke(
            None,
            config=node_config,
        )
    return state


def execute_next(app, thread_config):
    state = app.invoke(
        Command(resume=True),
        config=thread_config,
    )
    return state


# def execute_node(app, thread_config, node_id, state):
#     state = app.invoke(
#         Command(resume=state),
#         config=thread_config,
#     )
#     return state


# def human_evaluation(state):
#     print("interrupting...")
#     print(state)
#     interrupt("Please provide feedback:")
#     return state


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
