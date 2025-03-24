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


async def execution_plan(
    primitive_tasks: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
) -> list[PrimitiveTaskExecution]:
    plan = []
    # Initialize with default content key with schema
    document_keys = [{"key": "content", "schema": "str"}]
    transformed_data_keys = []
    current_state_key = "documents"
    for primitive_task in primitive_tasks:
        # Use the appropriate existing_keys based on current_state_key
        existing_keys = document_keys if current_state_key == "documents" else transformed_data_keys

        try:
            input_keys = await autogen_utils.run_input_key_generation_agent(
                primitive_task, existing_keys, model=model, api_key=api_key
            )
            # Check if all required keys exist in existing keys
            existing_key_names = [k["key"] if isinstance(k, dict) else k for k in existing_keys]
            input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]
            assert all(k in existing_key_names for k in input_key_names)
        except AssertionError:
            input_keys = await autogen_utils.run_input_key_generation_agent(
                primitive_task, [], model=model, api_key=api_key
            )
            existing_key_names = [k["key"] if isinstance(k, dict) else k for k in existing_keys]
            input_key_names = [k["key"] if isinstance(k, dict) else k for k in input_keys]

        # Handle local tools tasks differently
        if primitive_task["label"] == "Data Transformation":
            # For data transformation, we'll use the data_transform_tool
            try:
                # use the data transform agent to generate a plan
                transform_config = await autogen_utils.run_data_transform_plan_agent(
                    primitive_task, existing_keys, model=model, api_key=api_key
                )
                transform_plan = create_data_transform_plan(
                    primitive_task,
                    transform_config.get("operation", "transform"),
                    transform_config.get("parameters", {}),
                    existing_keys,  # Pass input keys with detailed schemas
                    current_state_key
                )
                plan.append(transform_plan)

                current_state_key = "transformed_data"

                output_json = extract_json_content(transform_config["parameters"]["output_schema"], True)
                for key in output_json:
                    transformed_data_keys.append({
                        "key": key,
                        "schema": output_json[key]
                    })

                # Add output key to existing keys with the detailed output schema
                # output_key = transform_plan["state_output_key"]
                # output_schema = transform_config["parameters"]["output_schema"]
                #
                # current_state_key = "transformed_data"
                # transformed_data_keys.append({
                #     "key": output_key,
                #     "schema": output_schema
                # })
                # # Add the output key with its schema to the appropriate existing keys
                # if current_state_key == "documents":
                #     document_keys.append({
                #         "key": output_key,
                #         "schema": output_schema
                #     })
                # else:
                #     transformed_data_keys.append({
                #         "key": output_key,
                #         "schema": output_schema
                #     })
                continue
            except Exception as e:
                # Fall back to default prompting plan if agent fails
                print(f"Error using data transform agent: {e}. Using default prompting plan.")

        if primitive_task["label"] == "Clustering Analysis":
            try:
                # Use the clustering agent to generate a plan
                clustering_config = await autogen_utils.run_clustering_plan_agent(
                    primitive_task, existing_keys, model=model, api_key=api_key
                )
                clustering_plan = create_clustering_plan(
                    primitive_task,
                    clustering_config.get("algorithm", "kmeans"),
                    clustering_config.get("parameters", {}),
                    existing_keys,
                    current_state_key
                )
                plan.append(clustering_plan)

                # Add output key to existing keys with the detailed output schema
                output_key = clustering_plan["state_output_key"]
                output_schema = clustering_plan.get("output_schema")

                # Add the output key to the appropriate existing keys
                if current_state_key == "documents":
                    document_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                else:
                    transformed_data_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                continue
            except Exception as e:
                print(f"Error using clustering agent: {e}. Using default prompting plan.")

        if primitive_task["label"] == "Dimensionality Reduction":
            try:
                # Use the dimension reduction agent to generate a plan
                dim_reduction_config = await autogen_utils.run_dim_reduction_plan_agent(
                    primitive_task, existing_keys, model=model, api_key=api_key
                )
                dim_reduction_plan = create_dim_reduction_plan(
                    primitive_task,
                    dim_reduction_config.get("algorithm", "pca"),
                    dim_reduction_config.get("parameters", {}),
                    existing_keys,
                    current_state_key
                )
                plan.append(dim_reduction_plan)

                # Add output key to existing keys with the detailed output schema
                output_key = dim_reduction_plan["state_output_key"]
                output_schema = dim_reduction_plan.get("output_schema")

                # Add the output key to the appropriate existing keys
                if current_state_key == "documents":
                    document_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                else:
                    transformed_data_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                continue
            except Exception as e:
                print(f"Error using dimension reduction agent: {e}. Using default prompting plan.")

        if primitive_task["label"] == "Embedding Generation":
            try:
                # Use the embedding agent to generate a plan
                embedding_config = await autogen_utils.run_embedding_plan_agent(
                    primitive_task, existing_keys, model=model, api_key=api_key
                )
                embedding_plan = create_embedding_plan(
                    primitive_task,
                    embedding_config.get("provider", "openai"),
                    embedding_config.get("parameters", {}),
                    existing_keys,
                    current_state_key,
                    api_key
                )
                plan.append(embedding_plan)

                # Add output key to existing keys with the detailed output schema
                output_key = embedding_plan["state_output_key"]
                output_schema = embedding_plan.get("output_schema")

                # Add the output key to the appropriate existing keys
                if current_state_key == "documents":
                    document_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                else:
                    transformed_data_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                continue
            except Exception as e:
                print(f"Error using embedding agent: {e}. Using default prompting plan.")

        if primitive_task["label"] == "Segmentation":
            try:
                # Use the segmentation agent to generate a plan
                segmentation_config = await autogen_utils.run_segmentation_plan_agent(
                    primitive_task, existing_keys, model=model, api_key=api_key
                )
                segmentation_plan = create_segmentation_plan(
                    primitive_task,
                    segmentation_config.get("strategy", "paragraph"),
                    segmentation_config.get("parameters", {}),
                    existing_keys,
                    current_state_key
                )
                plan.append(segmentation_plan)

                # Add output key to existing keys with the detailed output schema
                output_key = segmentation_plan["state_output_key"]
                output_schema = segmentation_plan.get("output_schema")

                # Add the output key to the appropriate existing keys
                if current_state_key == "documents":
                    document_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                else:
                    transformed_data_keys.append({
                        "key": output_key,
                        "schema": output_schema
                    })
                continue
            except Exception as e:
                print(f"Error using segmentation agent: {e}. Using default prompting plan.")

        # Default to using prompt_generation_agent for other tasks
        prompt_config = await autogen_utils.run_prompt_generation_agent(
            primitive_task, input_keys, model=model, api_key=api_key
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
            output_schema = "str"

        # Add the output key to the appropriate existing keys
        if current_state_key == "documents":
            document_keys.append({"key": output_key, "schema": output_schema})
        else:
            transformed_data_keys.append({"key": output_key, "schema": output_schema})

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
        plan.append(
            {
                **primitive_task,
                "state_input_key": current_state_key,
                "doc_input_keys": input_key_names,
                "state_output_key": output_key,
                # "input_key_schemas": input_key_schemas,
                # "output_schema": output_schema,
                "execution": {
                    "tool": "prompt_tool",
                    "parameters": {
                        "name": primitive_task["label"],
                        "model": model,
                        "api_key": api_key,
                        "format": "json",
                        "prompt_template": prompt_template,
                        "input_key_schemas": input_key_schemas,
                        "output_schema": output_schema,
                    },
                },
            }
        )
    return plan


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
        step.config for step in state_history if step.next[0] == f"{node_id}_evaluation"
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
        get_input = lambda state: get_input_func(state, state_input_key, doc_input_keys, step["execution"])
    else:
        get_input = custom_get_input_func
    # how to produce output
    if custom_reduce_func is None:
        if state_input_key == "transformed_data" or step["execution"]["tool"] in ["clustering_tool", "embedding_tool", "dim_reduction_tool", "segmentation_tool", "data_transform_tool"]:
            reduce = lambda combined: tools_reduce_func(
                combined, state_input_key, state_output_key, state_output_key
            )
        else:
            reduce = lambda combined: reduce_func(
                combined, state_input_key, state_output_key
            )
    else:
        reduce = custom_reduce_func
    # create the map-reduce chain
    # for clustering, dim reduction, data transformation the input is all documents
    # We cannot do batch process document by document
    if step["execution"]["tool"] in ["clustering_tool", "data_transform_tool", "dim_reduction_tool"]:
        map = RunnableAssign(
            {
                state_output_key: get_input
                | execution_chain
            }
        )
    else:
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


def tools_reduce_func(
    combined: dict,
    state_input_key: str,
    state_output_key: str,
    label_key: str = "output",
):
    """
    Updates the state with output data, handling both document-based and transformed data operations.

    Args:
        combined (dict): State with input and output keys
        state_input_key (str): Key for input data ("documents" or "transformed_data")
        state_output_key (str): Key for output data
        label_key (str): Default key for labeling documents when output is a simple value

    Returns:
        dict: Updated state with properly merged output data
    """
    output_data = combined[state_output_key]

    # Get input data or use appropriate empty container if missing
    input_data = combined.get(state_input_key, [] if state_input_key == "documents" else {})
    result = {state_input_key: input_data}

    # Handle operations based on input and output types

    # CASE 1: Working with transformed_data as input
    if state_input_key == "transformed_data":
        # Simply merge dictionaries or set the output directly
        if isinstance(output_data, dict):
            result["transformed_data"] = {**input_data, **output_data}
        else:
            # For non-dict outputs, store under the output key name
            result["transformed_data"] = dict(input_data)
            result["transformed_data"][label_key] = output_data
        return result

    # CASE 2: Documents as input, with transformed_data as output
    if state_output_key == "transformed_data" and isinstance(output_data, dict):
        result["transformed_data"] = output_data
        return result

    # CASE 3: Document mapping operations (output matches documents)
    if state_input_key == "documents" and isinstance(output_data, list):
        # For lists matching document length, apply outputs to each document
        if isinstance(input_data, list) and len(output_data) == len(input_data):
            updated_docs = []
            for doc, output in zip(input_data, output_data):
                if isinstance(output, dict):
                    updated_docs.append({**doc, **output})
                else:
                    updated_docs.append({**doc, label_key: output})
            result[state_input_key] = updated_docs
        else:
            # For other list outputs (like filtering), directly use the output
            result[state_input_key] = output_data
        return result

    # CASE 4: Documents as input with dictionary output (not transformed_data)
    if state_input_key == "documents" and isinstance(output_data, dict):
        # Store dictionary outputs in transformed_data
        result["transformed_data"] = output_data
        return result

    # CASE 5: Fallback - store output under its key name
    result[state_output_key] = output_data
    return result


# an empty node that is the root of the graph
def create_root():
    return RunnableLambda(func=lambda x: x)


# a common get input function
def get_input_func(state, state_input_key: str, doc_input_keys: list[str], execution = None):
    """
    Extract the required input fields from each document in the state.

    Args:
        state: The current state containing documents
        state_input_key: The key to access documents in the state
        doc_input_keys: The keys to extract from each document (can be strings or dicts with key/schema)

    Returns:
        A list of dictionaries containing only the required input fields from each document
        or the transformed data structure when state_input_key is 'transformed_data'
    """
    result = []
    key_schemas = {}
    feature_key = 'content'
    if execution and 'parameters' in execution and 'feature_key' in execution['parameters']:
        feature_key = execution['parameters']['feature_key']
    elif len(doc_input_keys) > 0:
        feature_key = doc_input_keys[0]
    try:
        key_schemas = execution['parameters']['input_key_schemas']
    except Exception:
        pass
    # For transformed_data, handle it specially
    if state_input_key == 'transformed_data':
        # handle each key in the global transformed data store, ideally there should be only one key.
        for key in doc_input_keys:
            if key in key_schemas:
                schema = key_schemas[key]
                # TODO: schema validation/transform here, e.g. ensure data is an array.
            transformed_data = state[state_input_key][key]
            if isinstance(transformed_data, list):
                for d in transformed_data:
                    result.append({
                        feature_key: d
                    })
            else:
                result.append({
                    feature_key: transformed_data
                })

    else:
        docs = state[state_input_key]  # how to get the list of docs from the state (e.g. state["documents"])
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

    return result


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
        extra_params = {k: v for k, v in spec["parameters"].items()
                        if k not in ["name", "algorithm", "feature_key", "n_components",
                                     "input_key_schemas", "output_schema"]}
        return RunnableLambda(
            lambda inputs: dim_reduction_tool(
                inputs,
                algorithm=algorithm,
                feature_key=feature_key,
                n_components=n_components,
                **extra_params
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
                api_key=api_key
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
                api_key=api_key
            )
        )

    # Segmentation Tool
    elif spec["tool"] == "segmentation_tool":
        strategy = spec["parameters"].get("strategy", "paragraph")
        content_key = spec["parameters"].get("content_key", "content")
        output_key = spec["parameters"].get("output_key", "segments")
        # Extract any other parameters for specific strategies
        extra_params = {k: v for k, v in spec["parameters"].items()
                        if k not in ["name", "strategy", "content_key", "output_key",
                                     "input_key_schemas", "output_schema"]}

        return RunnableLambda(
            lambda inputs: segmentation_tool(
                inputs,
                strategy=strategy,
                content_key=content_key,
                output_key=output_key,
                **extra_params
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
                wrap_result=wrap_result
            )
        )
    else:
        raise ValueError(f"Unknown execution type: {spec}")


def create_data_transform_plan(
        primitive_task,
        operation=None,
        config_params=None,
        input_keys=None,
        current_state_key="documents"
):
    """
    Creates an execution plan for data transformation tasks based on operation type.

    Args:
        primitive_task: The primitive task description
        operation: Optional operation type (map, filter, reduce, chain)
        config_params: Optional configuration parameters
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

    # Determine default output schema based on operation
    default_output_schema = None
    if operation == "reduce":
        # For reduce operations, use a structured schema template
        default_output_schema = {
            "result": "any"
        }
    else:
        # Filter and map operations typically maintain the same schema as input..
        if input_keys and len(input_keys) > 0 and isinstance(input_keys[0], dict) and "schema" in input_keys[0]:
            # Use the schema of the first input key as template
            default_output_schema = input_keys[0]["schema"]
        else:
            default_output_schema = {"content": "str"}

    output_key = "transformed_data"
    parameters = {
        "name": primitive_task["label"],
        "operation": operation,
        "input_key_schemas": input_key_schemas,
        "output_schema": default_output_schema
    }

    # If config_params is provided, use them
    if config_params:
        parameters.update(config_params)

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        # "input_key_schemas": input_key_schemas,  # Add detailed schema information to the plan
        "state_output_key": output_key,
        "execution": {
            "tool": "data_transform_tool",
            "parameters": parameters,
        },
    }

def create_clustering_plan(
    primitive_task,
    algorithm=None,
    config_params=None,
    input_keys=None,
    current_state_key="documents"
):
    """
    Creates an execution plan for clustering tasks based on algorithm type.

    Args:
        primitive_task: The primitive task description
        algorithm: Optional clustering algorithm (kmeans, dbscan, etc.)
        config_params: Optional configuration parameters
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

    default_output_schema = {
        "labels": "list[int]"
    }
    output_key = "cluster_labels"
    default_algorithm = "kmeans"

    parameters = {
        "name": primitive_task["label"],
        "algorithm": algorithm or default_algorithm,
        "feature_key": config_params.get("feature_key", "content"),
        "n_clusters": 3,  # Default number of clusters
        "input_key_schemas": input_key_schemas,
        "output_schema": default_output_schema
    }

    # If config_params is provided, use them
    if config_params:
        parameters.update(config_params)

        # If output_schema isn't in the provided parameters, add the default
        if "output_schema" not in parameters:
            parameters["output_schema"] = default_output_schema

    # Extract the output schema for state tracking
    output_schema = parameters.get("output_schema", default_output_schema)

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        # "input_key_schemas": input_key_schemas,
        # "output_schema": output_schema,
        "state_output_key": output_key,
        "execution": {
            "tool": "clustering_tool",
            "parameters": parameters,
        },
    }

def create_dim_reduction_plan(
    primitive_task,
    algorithm=None,
    config_params=None,
    input_keys=None,
    current_state_key="documents"
):
    """
    Creates an execution plan for dimensionality reduction tasks based on algorithm type.

    Args:
        primitive_task: The primitive task description
        algorithm: Optional dimensionality reduction algorithm (pca, tsne, umap)
        config_params: Optional configuration parameters
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
    default_output_schema = {
        "properties": {
            "reduced_dimensions": "list[list[float]]"
        }
    }

    output_key = "reduced_dimensions"
    default_algorithm = "pca"  # Default algorithm

    # Set up parameters
    parameters = {
        "name": primitive_task["label"],
        "algorithm": algorithm or default_algorithm,
        "feature_key": config_params.get("feature_key", "content"),
        "n_components": 2,  # Default number of dimensions to reduce to
        "input_key_schemas": input_key_schemas,
        "output_schema": default_output_schema
    }

    # If config_params is provided, use them
    if config_params:
        parameters.update(config_params)

        # If output_schema isn't in the provided parameters, add the default
        if "output_schema" not in parameters:
            parameters["output_schema"] = default_output_schema

    # Extract the output schema for state tracking
    output_schema = parameters.get("output_schema", default_output_schema)

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        # "input_key_schemas": input_key_schemas,
        # "output_schema": output_schema,
        "state_output_key": output_key,
        "execution": {
            "tool": "dim_reduction_tool",
            "parameters": parameters,
        },
    }

def create_embedding_plan(
    primitive_task,
    provider=None,
    config_params=None,
    input_keys=None,
    current_state_key="documents",
    api_key=""
):
    """
    Creates an execution plan for embedding tasks based on provider type.

    Args:
        primitive_task: The primitive task description
        provider: Optional embedding provider (openai, sentence_transformers)
        config_params: Optional configuration parameters
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
    default_output_schema = {
        "embedding": "list[float]"
    }

    output_key = "embedding"
    default_provider = "openai"  # Default provider
    default_model = "text-embedding-ada-002"  # Default model

    # Set up parameters
    parameters = {
        "name": primitive_task["label"],
        "provider": provider or default_provider,
        "model": default_model,
        "feature_key": config_params.get("feature_key", "content"),
        "input_key_schemas": input_key_schemas,
        "output_schema": default_output_schema,
        "api_key": api_key,
    }

    # If config_params is provided, use them
    if config_params:
        parameters.update(config_params)

        # If output_schema isn't in the provided parameters, add the default
        if "output_schema" not in parameters:
            parameters["output_schema"] = default_output_schema

    # Extract the output schema for state tracking
    output_schema = parameters.get("output_schema", default_output_schema)

    # Use batch embedding tool for efficiency
    tool_name = "embedding_tool"

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        # "input_key_schemas": input_key_schemas,
        # "output_schema": output_schema,
        "state_output_key": output_key,
        "execution": {
            "tool": tool_name,
            "parameters": parameters,
        },
    }

def create_segmentation_plan(
    primitive_task,
    strategy=None,
    config_params=None,
    input_keys=None,
    current_state_key="documents"
):
    """
    Creates an execution plan for segmentation tasks based on strategy type.

    Args:
        primitive_task: The primitive task description
        strategy: Optional segmentation strategy (paragraph, sentence, fixed_length, semantic)
        config_params: Optional configuration parameters
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
    default_output_schema = {
        "properties": {
            "segments": "list[str]"
        }
    }

    output_key = "segments"
    default_strategy = "paragraph"

    parameters = {
        "name": primitive_task["label"],
        "strategy": strategy or default_strategy,
        "content_key": "content",  # Default content key
        "output_key": output_key,  # Default output key
        "input_key_schemas": input_key_schemas,
        "output_schema": default_output_schema
    }

    # If config_params is provided, use them
    if config_params:
        parameters.update(config_params)

        # If output_schema isn't in the provided parameters, add the default
        if "output_schema" not in parameters:
            parameters["output_schema"] = default_output_schema

    # Extract the output schema for state tracking
    output_schema = parameters.get("output_schema", default_output_schema)

    return {
        **primitive_task,
        "state_input_key": current_state_key,
        "doc_input_keys": input_key_names,
        # "input_key_schemas": input_key_schemas,
        # "output_schema": output_schema,
        "state_output_key": output_key,
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