import logging
import sys
import os

from server.executor.tools import embedding_tool
from server.executor.tools.embedding_tool import embedding_tool, batch_embedding_tool
from server.executor.tools.clustering_tool import clustering_tool
from server.executor.tools.data_transform_tool import data_transform_tool
from server.executor.tools.dim_reduction_tool import dim_reduction_tool
from server.executor.tools.segmentation_tool import segmentation_tool
from server.AutoGenUtils import query as autogen_utils
from server.utils import extract_json_content

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import re
import copy
from typing import Annotated, Literal, TypedDict, Dict, List, Any
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

LOCAL_TOOL_TASKS = [
    "Data Transformation",
    "Clustering Analysis",
    "Dimensionality Reduction",
    "Embedding Generation",
    "Segmentation",
]


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


def find_last_state(graph, execute_node, thread_config):
    state_history = list(
        reversed([step for step in graph.get_state_history(thread_config)])
    )
    print([step.next[0] for step in state_history])
    if len(state_history) == 0:
        return None
    past_states = [
        step.values for step in state_history if step.next[0] == execute_node
    ]
    if len(past_states) == 0:
        return None
    return past_states[-1]


def collect_keys(
    primitive_tasks,
):
    all_states_and_keys = {
        "documents": [{"key": "content", "schema": "str"}],
    }
    # if there's key changed, we need to always update the subsequent tasks until there's no key changes
    plan = []
    for primitive_task in primitive_tasks:
        if "state_output_key" not in primitive_task:
            plan.append({**primitive_task})
            continue
        # if skipping parameter, we just add the user's defined task parameters to plan, we won't change keys neither
        # Add the output key to existing keys
        output_key = primitive_task["state_output_key"]
        output_schema = primitive_task["execution"]["parameters"]["output_schema"]
        states_in_this_step = copy.deepcopy(all_states_and_keys)

        # Track the key with its appropriate state
        state_input_key = primitive_task.get("state_input_key", "documents")
        # Add the output key to **original** input state
        update_state_keys(
            all_states_and_keys, state_input_key, output_key, output_schema
        )

        # If output is a list type, also add it to the global state
        add_output_list_to_global_state(all_states_and_keys, output_key, output_schema)
        primitive_task["available_states"] = states_in_this_step
        plan.append({**primitive_task})
        continue
    return plan


async def execution_plan(
    primitive_tasks: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
    compile_target: str | None = None,
    skip_IO: bool = False,
    skip_parameters: bool = False,
) -> list[PrimitiveTaskExecution]:
    plan = []
    # Track all states and their keys in a dictionary
    all_states_and_keys = {
        "documents": [{"key": "content", "schema": "str"}],
    }
    # if there's key changed, we need to always update the subsequent tasks until there's no key changes
    last_key_changed = False
    for primitive_task in primitive_tasks:
        # if skipping parameter, we just add the user's defined task parameters to plan, we won't change keys neither
        if (
            compile_target is not None
            and compile_target != primitive_task["id"]
            and not last_key_changed
        ) or skip_parameters:
            # Add the output key to existing keys
            output_key = primitive_task["state_output_key"]
            output_schema = primitive_task["execution"]["parameters"]["output_schema"]
            states_in_this_step = copy.deepcopy(all_states_and_keys)

            # Track the key with its appropriate state
            state_input_key = primitive_task.get("state_input_key", "documents")
            # Add the output key to **original** input state
            update_state_keys(
                all_states_and_keys, state_input_key, output_key, output_schema
            )

            # If output is a list type, also add it to the global state
            add_output_list_to_global_state(
                all_states_and_keys, output_key, output_schema
            )
            primitive_task["available_states"] = states_in_this_step
            plan.append({**primitive_task})
            continue

        if skip_IO:
            input_keys, input_key_names = (
                primitive_task["input_keys"],
                primitive_task["doc_input_keys"],
            )
            input_keys = [k for k in input_keys if k["key"] in input_key_names]
            state_input_key = primitive_task.get("state_input_key", "documents")
        else:
            # Generate input keys and input state
            single_key = False
            if primitive_task["label"] in [
                "Embedding Generation",
                "Clustering Analysis",
                "Dimensionality Reduction",
                "Data Transformation",
                "Segmentation",
            ]:
                single_key = True

            # generate input keys and the corresponding input state for this primitive task
            input_keys, input_key_names, state_input_key = await generate_input_keys(
                primitive_task,
                model,
                api_key,
                single_key_only=single_key,
                all_states_and_keys=all_states_and_keys,  # Pass all states and keys for LLM to decide which to use.
            )

        # plan will be added within this function
        await generate_execution_parameters(
            plan,
            primitive_task,
            state_input_key,
            input_keys,
            input_key_names,
            all_states_and_keys,  # Pass all state and keys dictionary
            model,
            api_key,
            skip_IO,
            skip_parameters,
        )

        last_key_changed = (
            "state_output_key" in primitive_task
            and primitive_task["state_output_key"] != plan[-1]["state_output_key"]
        )

    return plan


async def generate_input_keys(
    primitive_task, model, api_key, single_key_only=False, all_states_and_keys=None
):
    """
    Generate input keys and the corresponding state key for a primitive task by querying the LLM.

    Args:
        primitive_task: The primitive task description
        model: The LLM model to use
        api_key: API key for the LLM
        single_key_only: If True, ask the LLM to return only one key
        all_states_and_keys: All available state keys in the system

    Returns:
        Tuple of (input_keys, input_key_names, state_input_key)
    """
    # Default state key is "documents"
    state_input_key = "documents"

    # Keep track of keys by state
    all_states_and_keys = all_states_and_keys or {
        "documents": [{"key": "content", "schema": "str"}],
    }

    # Group keys by state for the LLM prompt
    keys_by_state = {}
    key_to_state_map = {}  # Map from key name to which state it belongs to

    for state, keys in all_states_and_keys.items():
        keys_by_state[state] = []
        for key in keys:
            key_name = key["key"] if isinstance(key, dict) else key
            keys_by_state[state].append(key)
            key_to_state_map[key_name] = state

    # Flatten all keys for validation
    all_keys = []
    for keys in keys_by_state.values():
        all_keys.extend(keys)

    try:
        # Call the input key generation agent with the state-aware prompt
        response = await autogen_utils.run_input_key_generation_agent(
            primitive_task,
            model=model,
            api_key=api_key,
            single_key_only=single_key_only,
            keys_by_state=keys_by_state,  # Pass grouped keys for state-aware prompting
        )

        # Extract input keys and the selected state
        input_keys = response

        # If the response includes a selected_state, use it directly
        if (
            isinstance(response, dict)
            and "required_keys" in response
            and "selected_state" in response
        ):
            state_input_key = response["selected_state"]
            input_keys = response["required_keys"]

        # Extract key names
        input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]

        # Validate that all requested keys exist
        all_key_names = [k["key"] if isinstance(k, dict) else k for k in all_keys]
        assert all(k in all_key_names for k in input_key_names)

        # Verify all keys are from the same state
        key_states = [key_to_state_map.get(k, "documents") for k in input_key_names]
        unique_states = set(key_states)

        if len(unique_states) > 1:
            # The LLM picked keys from different states, which is not allowed
            # Fall back to use only keys from the first state mentioned
            first_state = key_states[0]
            filtered_input_keys = [
                key for i, key in enumerate(input_keys) if key_states[i] == first_state
            ]
            if not filtered_input_keys:
                # If somehow we filtered out all keys, default to the first key
                filtered_input_keys = [input_keys[0]]

            input_keys = filtered_input_keys
            input_key_names = [
                k["key"] if isinstance(k, dict) else k for k in input_keys
            ]
            state_input_key = key_to_state_map.get(input_key_names[0], "documents")
        else:
            # All keys are from the same state, use that state
            state_input_key = key_states[0] if key_states else "documents"

        return input_keys, input_key_names, state_input_key
    except AssertionError as e:
        print(f"Error in input key generation: {e}")
        # Fallback approach if the keys don't exist
        input_keys = await autogen_utils.run_input_key_generation_agent(
            primitive_task,
            model=model,
            api_key=api_key,
            single_key_only=single_key_only,
        )

        # Handle new response format
        if isinstance(input_keys, dict) and "required_keys" in input_keys:
            input_keys = input_keys["required_keys"]

        input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]

        # Default to documents state if we can't find keys
        return input_keys, input_key_names, "documents"


async def generate_execution_parameters(
    plans,
    primitive_task,
    state_input_key,
    input_keys,
    input_key_names,
    all_states_and_keys,
    model,
    api_key,
    skip_io=False,
    skip_parameters=False,
):
    states_in_this_step = copy.deepcopy(all_states_and_keys)
    # Handle local tools tasks differently
    if primitive_task["label"] in LOCAL_TOOL_TASKS:
        try:
            if primitive_task["label"] == "Data Transformation":
                # For data transformation, we'll use the data_transform_tool
                # and use the data transform agent to generate a plan
                tool_config = await autogen_utils.run_data_transform_plan_agent(
                    primitive_task,
                    input_keys,
                    state_input_key,
                    all_states_and_keys,
                    model=model,
                    api_key=api_key,
                )
                tool_plan = create_data_transform_plan(
                    primitive_task,
                    tool_config,
                    input_keys,
                    state_input_key,
                )
                output_schema = tool_plan["execution"]["parameters"].get(
                    "output_schema", "list[str]"
                )

            elif primitive_task["label"] == "Clustering Analysis":
                if len(input_keys) > 1:
                    input_keys = input_keys[:1]
                # Use the clustering agent to generate a plan
                tool_config = await autogen_utils.run_clustering_plan_agent(
                    primitive_task,
                    input_keys,
                    state_input_key,
                    all_states_and_keys,
                    model=model,
                    api_key=api_key,
                )
                tool_plan = create_clustering_plan(
                    primitive_task,
                    tool_config,
                    input_keys,
                    state_input_key,
                )
                output_schema = tool_plan["execution"]["parameters"].get(
                    "output_schema", "list[int]"
                )

            elif primitive_task["label"] == "Dimensionality Reduction":
                if len(input_keys) > 1:
                    input_keys = input_keys[:1]
                # Use the dimension reduction agent to generate a plan
                tool_config = await autogen_utils.run_dim_reduction_plan_agent(
                    primitive_task,
                    input_keys,
                    state_input_key,
                    all_states_and_keys,
                    model=model,
                    api_key=api_key,
                )
                tool_plan = create_dim_reduction_plan(
                    primitive_task,
                    tool_config,
                    input_keys,
                    state_input_key,
                )
                output_schema = tool_plan["execution"]["parameters"].get(
                    "output_schema", "list[list[float]]"
                )

            elif primitive_task["label"] == "Embedding Generation":
                if len(input_keys) > 1:
                    input_keys = input_keys[:1]
                # Use the embedding agent to generate a plan
                tool_config = await autogen_utils.run_embedding_plan_agent(
                    primitive_task,
                    input_keys,
                    state_input_key,
                    all_states_and_keys,
                    model=model,
                    api_key=api_key,
                )
                tool_plan = create_embedding_plan(
                    primitive_task,
                    tool_config,
                    input_keys,
                    state_input_key,
                    api_key,
                )
                output_schema = tool_plan["execution"]["parameters"].get(
                    "output_schema", "list[float]"
                )

            elif primitive_task["label"] == "Segmentation":
                if len(input_keys) > 1:
                    input_keys = input_keys[:1]
                # Use the segmentation agent to generate a plan
                tool_config = await autogen_utils.run_segmentation_plan_agent(
                    primitive_task,
                    input_keys,
                    state_input_key,
                    all_states_and_keys,
                    model=model,
                    api_key=api_key,
                )
                tool_plan = create_segmentation_plan(
                    primitive_task,
                    tool_config,
                    input_keys,
                    state_input_key,
                )
                output_schema = tool_plan["execution"]["parameters"].get(
                    "output_schema", "list[str]"
                )

            if skip_io:
                output_key = primitive_task["state_output_key"]
                output_schema = primitive_task["execution"]["parameters"][
                    "output_schema"
                ]
                tool_plan["execution"]["parameters"]["output_schema"] = output_schema
                tool_plan["state_output_key"] = output_key
            else:
                output_key = tool_plan["state_output_key"]

            # Add the output key to original input state
            update_state_keys(
                all_states_and_keys, state_input_key, output_key, output_schema
            )

            # If output is a list type, also add it to the global state
            add_output_list_to_global_state(
                all_states_and_keys, output_key, output_schema
            )

            tool_plan["available_states"] = states_in_this_step
            plans.append(tool_plan)
            return
        except Exception as e:
            print(
                f"Error creating plan for {primitive_task['label']}: {e}. Using default prompting plan."
            )

    # Default to using prompt_generation_agent for other tasks
    prompt_config = await autogen_utils.run_prompt_generation_agent(
        primitive_task,
        input_keys,
        state_input_key,
        all_states_and_keys,
        model=model,
        api_key=api_key,
    )
    prompt_structured = prompt_config.get("prompt")
    output_schema = prompt_config.get("output_schema")
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
            prompt_structured["JSON_format"] = prompt_structured["JSON_format"].replace(
                "'", '"'
            )
        match = re.search(pattern, prompt_structured["JSON_format"])
        # Extract and print the result
        if match:
            output_key = match.group(1)
        # else:
        #     raise ValueError("Output key not found in JSON format")

        key_and_schema = extract_json_content(output_schema, True)
        # ideally output_schema should only have 1 key
        if key_and_schema:
            output_key, output_schema = next(iter(key_and_schema.items()))

    except Exception as e:
        print(e)
        output_key = primitive_task["label"] + "_output"
        output_schema = "str"

    if skip_io:
        prompt_structured["JSON_format"].replace(
            output_key, primitive_task["state_output_key"]
        )
        output_key = primitive_task["state_output_key"]
        output_schema = primitive_task["execution"]["parameters"]["output_schema"]

    # Add to input state
    update_state_keys(
        all_states_and_keys, state_input_key, output_key, str(output_schema)
    )

    # If output is a list type, also add it to the global state
    add_output_list_to_global_state(all_states_and_keys, output_key, str(output_schema))

    # replace {} in the JSON format with {{}}
    prompt_structured["JSON_format"] = (
        prompt_structured["JSON_format"].replace("{", "{{").replace("}", "}}")
    )
    input_key_schemas = get_input_key_schemas(input_keys)
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
            "content": "\n".join([f"{key}: {{{key}}}" for key in input_key_names]),
        },
    ]
    plans.append(
        {
            **primitive_task,
            "state_input_key": state_input_key,
            "doc_input_keys": input_key_names,
            "state_output_key": output_key,
            "available_states": states_in_this_step,
            "input_keys": input_keys,
            "execution": {
                "tool": "prompt_tool",
                "parameters": {
                    "name": primitive_task["label"],
                    "model": model,
                    "api_key": api_key,
                    "format": "json",
                    "prompt_template": prompt_template,
                    "input_key_schemas": input_key_schemas,
                    "output_schema": str(output_schema),
                },
            },
        }
    )
    return


def update_state_keys(all_states_and_keys, state_input_key, output_key, output_schema):
    if state_input_key not in all_states_and_keys:
        all_states_and_keys[state_input_key] = []
    all_states_and_keys[state_input_key].append(
        {"key": output_key, "schema": output_schema}
    )


def add_output_list_to_global_state(all_states_and_keys, output_key, output_schema):
    if output_schema.startswith("list["):
        # Add as a global state key
        if output_key not in all_states_and_keys:
            all_states_and_keys[output_key] = []
        # Extract the inner schema from list[...]
        inner_schema = output_schema[5:-1]  # Remove "list[" and "]"
        all_states_and_keys[output_key].append(
            {"key": output_key, "schema": inner_schema}
        )


def create_nodes(steps: list[PrimitiveTaskExecution]):
    return [create_node(step) for step in steps]


def create_graph(steps: list[PrimitiveTaskExecution], checkpointer=None):
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
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer), checkpointer


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
        # step.config for step in state_history if step.next[0] == f"{node_id}_evaluation"
        step.config
        for step in state_history
        if step.next[0] == f"{node_id}"
    ]
    if len(node_configs) == 0:
        return None
    if execution_version is None:
        return node_configs[-1]
    else:
        return node_configs[execution_version]


def execute_node(app, thread_config, node_id, execution_version=None, state=None):
    # if this is the first node executed in the graph
    # then we need to invoke with the initial state
    if len(list(app.get_state_history(thread_config))) == 0:
        new_state = app.invoke(state, config=thread_config)
        return new_state

    # if this is not the first node executed in the graph
    # check if this node is executed before
    node_config = get_node_config(app, thread_config, node_id, execution_version)
    if node_config is None:  # first time executing this node
        new_state = app.invoke(Command(resume=True), config=thread_config)
    else:  # if this node is executed before
        new_state = app.invoke(
            Command(goto=node_id, update=state),
            config=node_config,
        )
    return new_state


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
        get_input = lambda state: get_input_func(
            state, state_input_key, doc_input_keys, step["execution"]
        )
    else:
        get_input = custom_get_input_func

    # how to produce output
    if custom_reduce_func is None:
        # Special tools that need their own reduce function
        # if step["execution"]["tool"] in [
        #     "clustering_tool",
        #     "embedding_tool",
        #     "dim_reduction_tool",
        #     "segmentation_tool",
        #     "data_transform_tool",
        # ]:
        #     reduce = lambda combined: tools_reduce_func(
        #         combined, state_input_key, state_output_key, state_output_key
        #     )
        # else:
        #     reduce = lambda combined: reduce_func(
        #         combined, state_input_key, state_output_key
        #     )
        reduce = lambda combined: tools_reduce_func(
            combined, state_input_key, state_output_key, state_output_key
        )
    else:
        reduce = custom_reduce_func

    # create the map-reduce chain
    # for clustering, dim reduction, data transformation the input is all documents
    # We cannot do batch process document by document
    if step["execution"]["tool"] in [
        "clustering_tool",
        "data_transform_tool",
        "dim_reduction_tool",
    ]:
        map = RunnableAssign({state_output_key: get_input | execution_chain})
    else:
        """
        embedding_tool
        segmentation_tool
        prompt_tool
        """
        map = RunnableAssign(
            {
                state_output_key: get_input
                | RunnableLambda(
                    func=execution_chain.batch, afunc=execution_chain.abatch
                )
            }
        )
    map_reduce_chain = map | reduce
    return map_reduce_chain


# an empty node that is the root of the graph
def create_root():
    return RunnableLambda(func=lambda x: x)


# a common get input function
def get_input_func(
    state, state_input_key: str, doc_input_keys: list[str], execution=None
):
    """
    Extract the required input fields from each document in the state or directly from state keys.

    Args:
        state: The current state containing documents and other data
        state_input_key: The key to access data in the state ("documents" or any other state key)
        doc_input_keys: The keys to extract from each document (can be strings or dicts with key/schema)
        execution: Execution configuration

    Returns:
        A list of dictionaries containing only the required input fields
    """
    result = []
    key_schemas = {}
    feature_key = "content"
    if (
        execution
        and "parameters" in execution
        and "feature_key" in execution["parameters"]
    ):
        feature_key = execution["parameters"]["feature_key"]
    elif len(doc_input_keys) > 0:
        feature_key = doc_input_keys[0]
    try:
        key_schemas = execution["parameters"]["input_key_schemas"]
    except Exception:
        pass

    # For documents, extract fields from each document
    if state_input_key == "documents":
        docs = state["documents"]
        # Extract only the requested fields from each document
        for doc in docs:
            doc_data = {}
            for key in doc_input_keys:
                if key in doc:
                    # Get the value from the document
                    value = doc[key]

                    # Use schema information for potential data validation/conversion
                    if key in key_schemas:
                        schema = key_schemas[key]
                        # TODO: Here we could implement schema validation/conversion
                        # For example, ensure lists contain the right types, etc.

                    doc_data[key] = value
            result.append(doc_data)
    else:
        # For other state keys, retrieve directly from state
        if "global_store" not in state:
            state["global_store"] = {}
        if state_input_key in state["global_store"]:
            # If the state_input_key exists directly, use it
            data = state["global_store"][state_input_key]
            if isinstance(data, list):
                for d in data:
                    if isinstance(d, dict):
                        # Extract all requested fields from each dictionary in the list.
                        # This is the most common case.
                        doc_data = {}
                        for key in doc_input_keys:
                            if key in d:
                                doc_data[key] = d[key]
                        # If no fields were found, use the item as is, and use feature_key as the key.
                        if not doc_data:
                            result.append({feature_key: d})
                        else:
                            result.append(doc_data)
                    else:
                        # For non-dict items, use feature_key
                        # for example, [1, 2, 1] -> [{label_key: 1}, {label_key: 2}, {label_key: 1}]
                        result.append({feature_key: d})
            elif isinstance(data, dict):
                # NOTE: This should really not happen, but we do it anyway to avoid/recover from errors at best.
                # Try to extract all requested fields from the dictionary
                doc_data = {}
                for key in doc_input_keys:
                    if key in data:
                        doc_data[key] = data[key]
                # If no fields were found, ensure at least feature_key exists in input..
                if not doc_data:
                    doc_data[feature_key] = data
                result.append(doc_data)
            else:
                # For primitive values, use feature_key
                result.append({feature_key: data})
        else:
            # Otherwise, try to find all requested keys in the state
            # For each doc_input_key, look for a matching key in documents or global_store
            # NOTE: This should really not happen, but we do it anyway to avoid/recover from errors at best.
            for key in doc_input_keys:
                if (
                    isinstance(state["documents"], list)
                    and len(state["documents"]) > 0
                    and key in state["documents"][0]
                ):
                    result.extend([{key: doc[key]} for doc in state["documents"]])
                elif key in state["global_store"]:
                    data = state["global_store"][key]
                    if isinstance(data, list):
                        result.extend([{key: d} for d in data])

    return result


# a common reduce function
def reduce_func(combined: dict, state_input_key: str, state_output_key: str):
    outputs = combined[state_output_key]  # "summaries"
    result = {}
    if state_input_key == "documents":
        original_data = combined[state_input_key]  # i.e. "documents"
        # Create the base result with modified documents (original behavior)
        result = {
            "documents": [
                {**doc, **{k: v for k, v in output.items()}}
                for doc, output in zip(original_data, outputs)
            ]
        }
    # # Add outputs as a separate key if they are dictionaries containing lists
    # # this happens when we choose / change to non-documents states.
    # if outputs and isinstance(outputs, list) and len(outputs) > 0:
    #     # Merge with the existing global_store keys
    #     result['global_store'] = combined.get('global_store', {})
    #     merged_global_result = merge_list_results_to_global_list(outputs)
    #     if len(merged_global_result) > 0:
    #         result["global_store"][state_output_key] = merged_global_result

    return result


def tools_reduce_func(
    combined: dict,
    state_input_key: str,
    state_output_key: str,
    label_key: str = "item",
):
    """
    Updates the state with output data directly in the state object.

    Args:
        combined (dict): State with input and output keys
        state_input_key (str): Key for input data ("documents" or any other state key)
        state_output_key (str): Key for output data
        label_key (str): Default key for labeling documents when output is a simple value

    Returns:
        dict: Updated state with properly merged output data
    """
    output_data = combined[state_output_key]

    # Get input data or use appropriate empty container if missing
    result = dict(combined)

    # Handle operations based on input and output types

    # CASE 1: State key with matching list lengths, merging back with the input state key
    # This includes `documents` and `global_store` states
    merge_back_to_original_state(
        state_input_key, combined, output_data, result, label_key
    )

    # ALWAYS DO: store directly in state output key
    # Subcase 1: state input is documents, get results from each document, merge them, the output with the existing global_store keys
    if state_input_key == "documents":
        if should_merge_sublist_to_global(output_data, label_key):
            # Merge with the existing global_store keys
            result["global_store"] = combined.get("global_store", {})
            merged_global_result = merge_list_results_to_global_list(
                output_data, label_key
            )
            if len(merged_global_result) > 0:
                result["global_store"][state_output_key] = merged_global_result
    # Subcase 2: state input is not documents, but the output is a list
    elif isinstance(output_data, list):
        # TODO: make this more graceful by using labels to decide if we should flatten
        # print(len(output_data), isinstance(output_data[0], list), len(output_data[0]))
        if (
            len(output_data) > 0
            and isinstance(output_data[0], dict)
            and label_key in output_data[0]
            and isinstance(output_data[0][label_key], list)
            and len(output_data[0][label_key]) < 100
        ):
            # Flatten the list of lists to a single lis
            result["global_store"][state_output_key] = [
                {label_key: item}
                for sublist in output_data
                for item in sublist[label_key]
            ]
        else:
            # only embeddings should reach here
            result["global_store"][state_output_key] = [
                {label_key: v} for v in output_data
            ]
    # Subcase 3: state input is not documents, but the output is a dictionary
    # Note, this should not happen, but we do it anyway to avoid/recover from errors at best, it handles LLM responses like {"summary": {"summary": ["str1", "str2", ...]}}
    elif isinstance(output_data, dict):
        if state_output_key in output_data and isinstance(
            output_data[state_output_key], list
        ):
            result["global_store"][state_output_key] = [
                {label_key: v} for v in output_data[state_output_key]
            ]
        else:
            logging.warn(
                "No expected output key found in the result, using the first key by default."
            )
            _, res = next(iter(output_data.items()))
            result["global_store"][state_output_key] = res
    return result


def merge_back_to_original_state(
    state_input_key, combined, output_data, result, label_key
):
    if (
        state_input_key != "documents"
        and "global_store" in combined
        and state_input_key not in combined["global_store"]
    ):
        return
    input_data = (
        combined.get(state_input_key)
        if state_input_key == "documents"
        else combined.get("global_store").get(state_input_key)
    )
    if (
        isinstance(input_data, list)
        and isinstance(output_data, list)
        and len(input_data) == len(output_data)
    ):
        # For lists matching source length, apply outputs to each item
        updated_items = []
        for item, output in zip(input_data, output_data):
            if isinstance(item, dict) and isinstance(output, dict):
                updated_items.append({**item, **output})
            elif isinstance(item, dict):
                updated_items.append({**item, label_key: output})
            else:
                updated_items.append({label_key: output})
        if state_input_key == "documents":
            result[state_input_key] = updated_items
        else:
            result["global_store"][state_input_key] = updated_items


def should_merge_sublist_to_global(outputs, label_key="item"):
    if not isinstance(outputs, list) or len(outputs) == 0:
        return False
    if isinstance(outputs[0], dict):
        keys = outputs[0].keys()
        if label_key in keys and isinstance(outputs[0][label_key], list):
            return True
    if isinstance(outputs[0], list):
        return True
    return False


def merge_list_results_to_global_list(outputs: list, label_key="item"):
    """
    if outputs are lists like:
    [
      {'summary': ['str1', 'str2', ...]},
      {'summary': ['str1', 'str2', ...]}
    ]
    OR:
    [
      ['str1', 'str2', ...],
      ['str1', 'str2', ...]
    ]
    We will merge the outputs to one global array
    [{'summary': 'str1'}, {'summary': 'str2'}, ... {'summary': 'strn'}]
    """
    # Add outputs as a separate key if they are dictionaries containing lists
    merged_results = []
    for row in outputs:
        if isinstance(row, dict):
            if label_key in row and isinstance(row[label_key], list):
                merged_results.extend([{label_key: v} for v in row[label_key]])
            else:
                values = list(row.values())
                # there should only be one key for merging
                if values and isinstance(values[0], list):
                    merged_results.extend([{label_key: v} for v in values[0]])
        elif isinstance(row, list):
            merged_results.extend([{label_key: v} for v in row])
    return merged_results


def convert_spec_to_chain(spec):
    if spec["tool"] == "prompt_tool":
        return custom_tools.prompt_tool(
            spec["parameters"]["name"],
            custom_tools.parse_template(spec["parameters"]["prompt_template"]),
            spec["parameters"]["model"],
            spec["parameters"]["api_key"],
            spec["parameters"]["format"],
        )
    elif spec["tool"] == "clustering_tool":
        n_clusters = spec["parameters"].get("n_clusters", 3)
        feature_key = spec["parameters"].get("feature_key", "content")
        algorithm = spec["parameters"].get("algorithm", "kmeans")
        return RunnableLambda(
            lambda inputs: clustering_tool(
                inputs,
                n_clusters=n_clusters,
                feature_key=feature_key,
                algorithm=algorithm,
            )
        )
    elif spec["tool"] == "embedding_tool":
        api_key = spec["parameters"]["api_key"]
        model = spec["parameters"].get("model", "text-embedding-ada-002")
        feature_key = spec["parameters"].get("feature_key", "content")
        provider = spec["parameters"].get("provider", "openai")
        return RunnableLambda(
            lambda doc: embedding_tool(doc, api_key, model, feature_key, provider)
        )
    # Dimension Reduction Tool
    elif spec["tool"] == "dim_reduction_tool":
        algorithm = spec["parameters"].get("algorithm", "pca")
        feature_key = spec["parameters"].get("feature_key", "content")
        n_components = spec["parameters"].get("n_components", 2)
        # Extract any other parameters for specific algorithms
        extra_params = {
            k: v
            for k, v in spec["parameters"].items()
            if k
            not in [
                "name",
                "algorithm",
                "feature_key",
                "n_components",
                "input_key_schemas",
                "output_schema",
            ]
        }
        return RunnableLambda(
            lambda inputs: dim_reduction_tool(
                inputs,
                algorithm=algorithm,
                feature_key=feature_key,
                n_components=n_components,
                **extra_params,
            )
        )

    # Embedding Tools
    elif spec["tool"] == "embedding_tool":
        provider = spec["parameters"].get("provider", "openai")
        model = spec["parameters"].get("model", "text-embedding-ada-002")
        feature_key = spec["parameters"].get("feature_key", "content")
        api_key = spec["parameters"].get("api_key", None)

        return RunnableLambda(
            lambda inputs: embedding_tool(
                inputs,
                provider=provider,
                model=model,
                feature_key=feature_key,
                api_key=api_key,
            )
        )

    elif spec["tool"] == "batch_embedding_tool":
        provider = spec["parameters"].get("provider", "openai")
        model = spec["parameters"].get("model", "text-embedding-ada-002")
        feature_key = spec["parameters"].get("feature_key", "content")
        api_key = spec["parameters"].get("api_key", None)

        return RunnableLambda(
            lambda inputs: batch_embedding_tool(
                inputs,
                provider=provider,
                model=model,
                feature_key=feature_key,
                api_key=api_key,
            )
        )

    # Segmentation Tool
    elif spec["tool"] == "segmentation_tool":
        strategy = spec["parameters"].get("strategy", "paragraph")
        feature_key = spec["parameters"].get("feature_key", "content")
        output_key = spec["parameters"].get("output_key", "segments")
        # Extract any other parameters for specific strategies
        extra_params = {
            k: v
            for k, v in spec["parameters"].items()
            if k
            not in [
                "name",
                "strategy",
                "feature_key",
                "output_key",
                "input_key_schemas",
                "output_schema",
            ]
        }

        return RunnableLambda(
            lambda inputs: segmentation_tool(
                inputs,
                strategy=strategy,
                feature_key=feature_key,
                output_key=output_key,
                **extra_params,
            )
        )
    elif spec["tool"] == "data_transform_tool":
        # Extract parameters for data_transform_tool
        operation = spec["parameters"].get("operation", "transform")
        transform_code = spec["parameters"].get("transform_code", None)
        wrap_result = spec["parameters"].get("wrap_result", False)
        return RunnableLambda(
            lambda inputs: data_transform_tool(
                inputs,
                operation=operation,
                transform_code=transform_code,
                wrap_result=wrap_result,
            )
        )
    else:
        raise ValueError(f"Unknown execution type: {spec}")


def create_data_transform_plan(
    primitive_task,
    tool_config=None,
    input_keys=None,
    current_state_key="documents",
):
    """
    Creates an execution plan for data transformation tasks based on operation type.

    Args:
        primitive_task: The primitive task description
        tool_config: configuration parameters
        input_keys: Optional list of input keys with their detailed schemas
        current_state_key: Current langgraph state key

    Returns:
        A data transformation execution plan
    """
    # Default values
    # default_input_keys = [{"key": "content", "schema": "str"}]
    # input_keys = input_keys or default_input_keys

    # Extract just the key names for backward compatibility
    input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]

    input_key_schemas = get_input_key_schemas(input_keys)

    # default output schema
    output_schema = "str"

    # Default output key, will update later.
    state_output_key = "transformed_data"

    parameters = {
        "name": primitive_task["label"],
        "operation": tool_config.get("operation", "transform"),
        "input_key_schemas": input_key_schemas,
    }

    # If config_params is provided, use them
    # also update the state_output_key here
    if tool_config:
        if "parameters" in tool_config:
            parameters.update(tool_config.get("parameters", {}))
        if "output_schema" in tool_config:
            try:
                key_and_schema = extract_json_content(
                    tool_config["output_schema"], True
                )
                print("key and schema: ", key_and_schema)
                # ideally output_schema should only have 1 key
                if key_and_schema:
                    state_output_key, output_schema = next(iter(key_and_schema.items()))
            except Exception:
                pass
        parameters["output_schema"] = output_schema
    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        "input_keys": input_keys,
        "state_output_key": state_output_key,
        "execution": {
            "tool": "data_transform_tool",
            "parameters": parameters,
        },
    }


def create_clustering_plan(
    primitive_task,
    tool_config,
    input_keys=None,
    current_state_key="documents",
):
    """
    Creates an execution plan for clustering tasks based on algorithm type.

    Args:
        primitive_task: The primitive task description
        tool_config: configuration parameters
        input_keys: Optional list of input keys with their detailed schemas
        current_state_key: The current state key to use as input (default: "documents")

    Returns:
        A clustering execution plan
    """
    # Default values
    default_input_keys = [{"key": "embedding", "schema": "str"}]
    input_keys = input_keys or default_input_keys

    input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]

    # Get detailed schema information
    input_key_schemas = get_input_key_schemas(input_keys)

    output_schema = "list[int]"
    state_output_key = "cluster_labels"

    parameters = {
        "name": primitive_task["label"],
        "algorithm": tool_config.get("algorithm", "kmeans"),
        "feature_key": input_key_names[0],
        "n_clusters": 3,  # Default number of clusters
        "input_key_schemas": input_key_schemas,
    }
    # If config_params is provided, use them
    # also update the state_output_key here
    if tool_config:
        if "parameters" in tool_config:
            parameters.update(tool_config.get("parameters", {}))
        if "output_schema" in tool_config:
            try:
                key_and_schema = extract_json_content(
                    tool_config["output_schema"], True
                )
                # ideally output_schema should only have 1 key
                if key_and_schema:
                    state_output_key, output_schema = next(iter(key_and_schema.items()))
            except Exception:
                pass
        parameters["output_schema"] = output_schema

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        "input_keys": input_keys,
        "state_output_key": state_output_key,
        "execution": {
            "tool": "clustering_tool",
            "parameters": parameters,
        },
    }


def create_dim_reduction_plan(
    primitive_task,
    tool_config,
    input_keys=None,
    current_state_key="documents",
):
    """
    Creates an execution plan for dimensionality reduction tasks based on algorithm type.

    Args:
        primitive_task: The primitive task description
        tool_config: Configuration parameters
        input_keys: Optional list of input keys with their detailed schemas
        current_state_key: The current state key to use as input (default: "documents")

    Returns:
        A dimensionality reduction execution plan
    """
    # Default values
    default_input_keys = [{"key": "embedding", "schema": "list[float]"}]
    input_keys = input_keys or default_input_keys
    input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]

    input_key_schemas = get_input_key_schemas(input_keys)

    # Default output schema
    output_schema = "list[list[float]]"

    state_output_key = "reduced_dimensions"

    # Set up parameters
    parameters = {
        "name": primitive_task["label"],
        "algorithm": tool_config.get("algorithm", "pca"),
        "feature_key": input_key_names[0],
        "n_components": 2,  # Default number of dimensions to reduce to
        "input_key_schemas": input_key_schemas,
    }

    # If config_params is provided, use them
    # also update the state_output_key here
    if tool_config:
        if "parameters" in tool_config:
            parameters.update(tool_config.get("parameters", {}))
        if "output_schema" in tool_config:
            try:
                key_and_schema = extract_json_content(
                    tool_config["output_schema"], True
                )
                # ideally output_schema should only have 1 key
                if key_and_schema:
                    state_output_key, output_schema = next(iter(key_and_schema.items()))
            except Exception:
                pass
        parameters["output_schema"] = output_schema

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        "input_keys": input_keys,
        "state_output_key": state_output_key,
        "execution": {
            "tool": "dim_reduction_tool",
            "parameters": parameters,
        },
    }


def create_embedding_plan(
    primitive_task,
    tool_config,
    input_keys=None,
    current_state_key="documents",
    api_key="",
):
    """
    Creates an execution plan for embedding tasks based on provider type.

    Args:
        primitive_task: The primitive task description
        tool_config: Configuration parameters
        input_keys: Optional list of input keys with their detailed schemas
        current_state_key: The current state key to use as input (default: "documents")
        api_key: api key

    Returns:
        An embedding execution plan
    """
    # Default values
    default_input_keys = [{"key": "content", "schema": "str"}]
    input_keys = input_keys or default_input_keys

    input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]
    input_key_schemas = get_input_key_schemas(input_keys)

    # Default output schema
    output_schema = "list[float]"

    state_output_key = "embedding"
    default_model = "text-embedding-ada-002"  # Default model

    # Set up parameters
    parameters = {
        "name": primitive_task["label"],
        "provider": tool_config.get("provider", "openai"),
        "model": default_model,
        "feature_key": input_key_names[0],
        "input_key_schemas": input_key_schemas,
        "api_key": api_key,
    }

    # If config_params is provided, use them
    # also update the state_output_key here
    if tool_config:
        if "parameters" in tool_config:
            parameters.update(tool_config.get("parameters", {}))
        if "output_schema" in tool_config:
            try:
                key_and_schema = extract_json_content(
                    tool_config["output_schema"], True
                )
                # ideally output_schema should only have 1 key
                if key_and_schema:
                    state_output_key, output_schema = next(iter(key_and_schema.items()))
            except Exception:
                pass
        parameters["output_schema"] = output_schema

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        "input_keys": input_keys,
        "state_output_key": state_output_key,
        "execution": {
            "tool": "embedding_tool",
            "parameters": parameters,
        },
    }


def create_segmentation_plan(
    primitive_task,
    tool_config,
    input_keys=None,
    current_state_key="documents",
):
    """
    Creates an execution plan for segmentation tasks based on strategy type.

    Args:
        primitive_task: The primitive task description
        tool_config: Configuration parameters
        input_keys: Optional list of input keys with their detailed schemas
        current_state_key: The current state key to use as input (default: "documents")

    Returns:
        A segmentation execution plan
    """
    # Default values
    default_input_keys = [{"key": "content", "schema": "str"}]
    input_keys = input_keys or default_input_keys

    input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]
    # Get detailed schema information
    input_key_schemas = get_input_key_schemas(input_keys)

    # Default output schema
    output_schema = "list[str]"

    state_output_key = "segments"

    parameters = {
        "name": primitive_task["label"],
        "strategy": tool_config.get("strategy", "paragraph"),
        "feature_key": input_key_names[0],
        "input_key_schemas": input_key_schemas,
    }

    # If config_params is provided, use them
    # also update the state_output_key here
    if tool_config:
        if "parameters" in tool_config:
            parameters.update(tool_config.get("parameters", {}))
        if "output_schema" in tool_config:
            try:
                key_and_schema = extract_json_content(
                    tool_config["output_schema"], True
                )
                # ideally output_schema should only have 1 key
                if key_and_schema:
                    state_output_key, output_schema = next(iter(key_and_schema.items()))
            except Exception:
                pass
        parameters["output_schema"] = output_schema

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        "input_keys": input_keys,
        "state_output_key": state_output_key,
        "execution": {
            "tool": "segmentation_tool",
            "parameters": parameters,
        },
    }


def get_input_key_schemas(input_keys: list):
    input_key_schemas = {}
    for key in input_keys:
        if isinstance(key, dict):
            key_name = key["key"] if "key" in key else str(key)
            if "schema" in key:
                input_key_schemas[key_name] = key["schema"]
        elif isinstance(key, str):
            input_key_schemas[key] = "str"
    return input_key_schemas
