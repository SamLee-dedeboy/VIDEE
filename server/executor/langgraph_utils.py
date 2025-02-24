import sys
import os

from server.custom_types.custom_types import State

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import re
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
    PrimitiveTaskExecution,
    PrimitiveTaskDescription,
    UserExecutionState,
    BaseStateSchema,
)
import server.executor.tools as custom_tools
import server.AutoGenUtils.query as autogen_utils


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
            "executed": False,
            "executable": first_node,
            "childrenIds": children_dict[node],
            "parentIds": node_dict[node]["parentIds"],
        }
        first_node = False
    return user_execution_state


def update_execution_state(user_execution_state, node_id):
    user_execution_state[node_id]["executed"] = True
    executed_nodes = list(
        filter(
            lambda k: user_execution_state[k]["executed"], user_execution_state.keys()
        )
    )
    for child_node_id in user_execution_state[node_id]["childrenIds"]:
        if all(
            parent_id in executed_nodes
            for parent_id in user_execution_state[child_node_id]["parentIds"]
        ):
            user_execution_state[child_node_id]["executable"] = True
    return user_execution_state


async def execution_plan(
    primitive_tasks: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
) -> list[PrimitiveTaskExecution]:
    plan = []
    existing_keys = ["content"]
    for primitive_task in primitive_tasks:
        try:
            input_keys = await autogen_utils.run_input_key_generation_agent(
                primitive_task, existing_keys, model=model, api_key=api_key
            )
            assert all(k in existing_keys for k in input_keys)
        except AssertionError:
            input_keys = await autogen_utils.run_input_key_generation_agent(
                primitive_task, [], model=model, api_key=api_key
            )
        prompt_structured = await autogen_utils.run_prompt_generation_agent(
            primitive_task, input_keys, model=model, api_key=api_key
        )
        # extract output key from JSON format
        try:
            pattern = r'\{\s*"(\w+)"\s*:\s*'
            if isinstance(prompt_structured["JSON_format"], dict):
                prompt_structured["JSON_format"] = json.dumps(
                    prompt_structured["JSON_format"],
                    indent=4,
                    ensure_ascii=False,
                )
            else:
                prompt_structured["JSON_format"] = prompt_structured[
                    "JSON_format"
                ].replace("'", '"')
            match = re.search(pattern, prompt_structured["JSON_format"])
            # Extract and print the result
            if match:
                output_key = match.group(1)
            else:
                raise ValueError("Output key not found in JSON format")

        except ValueError as e:
            print(e)
            output_key = primitive_task["label"] + "_output"
        existing_keys.append(output_key)

        # replace {} in the JSON format with {{}}
        prompt_structured["JSON_format"] = (
            prompt_structured["JSON_format"].replace("{", "{{").replace("}", "}}")
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
                    {prompt_requirements}
                    Reply with the following JSON format:
                    {prompt_output_format}
                    """.format(
                    prompt_context=prompt_structured["Context"],
                    prompt_task=prompt_structured["Task"],
                    prompt_requirements=prompt_structured["Requirements"],
                    prompt_output_format=prompt_structured["JSON_format"],
                ),
            },
            {
                "role": "human",
                "content": "\n".join([f"{key}: {{{key}}}" for key in input_keys]),
            },
        ]
        plan.append(
            {
                **primitive_task,
                "state_input_key": "documents",
                "doc_input_keys": input_keys,
                "state_output_key": output_key,
                "execution": {
                    "tool": "prompt_tool",
                    "parameters": {
                        "name": primitive_task["label"],
                        "model": model,
                        "api_key": api_key,
                        "format": "json",
                        "prompt_template": prompt_template,
                    },
                },
            }
        )
    return plan


def create_nodes(steps: list[PrimitiveTaskExecution]):
    return [create_node(step) for step in steps]


def create_graph(steps: list[PrimitiveTaskExecution]):
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
        if step["execution"]["tool"] == "clustering_tool":
            reduce = lambda combined: clustering_reduce_func(combined, state_input_key, state_output_key)
        else:
            reduce = lambda combined: reduce_func(
                combined, state_input_key, state_output_key
            )
    else:
        reduce = custom_reduce_func
    # create the map-reduce chain
    # map = RunnableAssign(
    #     {
    #         state_output_key: get_input
    #         | RunnableLambda(func=execution_chain.batch, afunc=execution_chain.abatch)
    #     }
    # )
    map = RunnableAssign(
        {
            state_output_key: get_input
            | execution_chain
        }
    )
    map_reduce_chain = map | reduce
    return map_reduce_chain


def clustering_reduce_func(combined: dict, state_input_key: str, state_output_key: str,
                           label_key: str = "cluster_label"):
    """
    Assigns cluster labels to documents in the state.

    Args:
        combined (dict): State with input and output keys.
        state_input_key (str): Key for input documents (e.g., "documents").
        state_output_key (str): Key for cluster labels (e.g., "cluster_labels").
        label_key (str): Key to store labels in each document (default: "cluster_label").

    Returns:
        dict: Updated state with labels added to documents.
    """
    labels = combined[state_output_key]  # List of integers
    documents = combined[state_input_key]  # List of document dicts
    updated_documents = [{**doc, label_key: label} for doc, label in zip(documents, labels)]
    return {state_input_key: updated_documents}

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
    elif spec["tool"] == "agent_with_tools":
        # Create sub-graph for agent with tools
        tools = [custom_tools.calculator]  # Can be extended based on spec
        model = ChatOpenAI(model=spec["parameters"]["model"], api_key=spec["parameters"]["api_key"])
        model_with_tools = model.bind_tools(tools)

        # Define agent node
        def agent_node(state: State) -> State:
            messages = state["messages"]
            response = model_with_tools.invoke(messages)
            print("Agent response:", response)
            return {"messages": messages + [response]}

        # Define tool node
        tool_node = ToolNode(tools)

        # Define finish node to set state_output_key
        def finish_node(state: State) -> State:
            final_output = state["messages"][-1].content
            return {"messages": final_output}

        # Build sub-graph
        sub_graph = StateGraph(State)
        sub_graph.add_node("agent", agent_node)
        sub_graph.add_node("tools", tool_node)
        sub_graph.add_node("finish", finish_node)

        # Define condition for continuing
        def should_continue(state: State):
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return "finish"

        sub_graph.set_entry_point("agent")
        sub_graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "finish": "finish"})
        # sub_graph.add_edge("tools", "agent")
        sub_graph.add_edge("finish", END)

        sub_graph_runnable = sub_graph.compile()

        def process_single_input(input, sub_graph_runnable, messages):
            initial_state = {"messages": [HumanMessage(content="calculate 1+1*2")]}
            updated_state = sub_graph_runnable.invoke(initial_state)
            return updated_state["messages"]

        # Return a runnable that processes a single input
        return RunnableLambda(lambda input: process_single_input(input, sub_graph_runnable, spec["parameters"]["messages"]))

    elif spec["tool"] == "clustering_tool":
        n_clusters = spec["parameters"].get("n_clusters", 3)
        feature_key = spec["parameters"].get("feature_key", "embedding")
        # return custom_tools.clustering_chain.bind(n_clusters=n_clusters, feature_key=feature_key)
        return RunnableLambda(
            lambda inputs: custom_tools.clustering_tool(inputs, n_clusters=n_clusters, feature_key=feature_key)
        )
    else:
        raise ValueError(f"Unknown execution type: {spec}")
