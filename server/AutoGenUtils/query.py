import json
from server.custom_types import Node, PrimitiveTaskDescription
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from tqdm import tqdm
import asyncio

from server.utils import extract_json_content


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True, ensure_ascii=False)


async def call_agent(agent, user_message):
    response = await agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )
    return response


async def parallel_call_agents(n, agent, user_message):
    tasks = [call_agent(agent, user_message) for _ in range(n)]

    results = await asyncio.gather(*tasks)
    return results


async def run_goal_decomposition_agent(goal: str, model: str, api_key: str):
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    goal_decomposition_agent = AssistantAgent(
        name="goal_decomposition_agent",
        model_client=model_client,
        system_message="""You are a text analytics task planner. 
        Users have collected a dataset, and they need help with text analytics tasks.
        Users will describe a goal to you, and you need to help them decompose the goal into subtasks, and then provide a plan to complete each of the subtask.
        Ignore the other practical parts such as data collection, cleaning or visualization.
        Focus on the conceptual steps that are needed to complete the goal, with as few steps as possible .
        Reply with this JSON format:
            {
                "steps": [
                    {
                        "id": (int),
                        "label": (string)
                        "description": (string)
                        "explanation": (string, explain why this step is needed)
                        "depend_on": (int[], ids of the steps that this step depends on)
                    },
                    {
                        "id": (int),
                        "label": (string)
                        "description": (string)
                        "explanation": (string, explain why this step is needed)
                        "depend_on": (int[], ids of the steps that this step depends on)
                    },
                    ...
                ]
            }  """,
    )
    response = await goal_decomposition_agent.on_messages(
        [TextMessage(content=goal, source="user")],
        cancellation_token=CancellationToken(),
    )
    return extract_json_content(response.chat_message.content)["steps"]


async def run_goal_decomposition_agent_stepped(
    goal: str,
    previous_steps: list,
    model: str,
    api_key: str,
    temperature=0.0,
    n=1,
    remain_steps=10,
):
    if remain_steps <= 0:
        ids = list(map(lambda step: step["id"], previous_steps))
        return [
            {
                "id": "END_PATH_" + str(ids),
                "label": "END",
                "description": "END",
                "explanation": "END",
                "parentIds": ids,
            }
        ]

    if remain_steps <= 0:
        ids = list(map(lambda step: step["id"], previous_steps))
        return [
            {
                "id": "END_PATH_" + str(ids),
                "label": "END",
                "description": "END",
                "explanation": "END",
                "parentIds": ids,
            }
        ]

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=temperature,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    goal_decomposition_agent = AssistantAgent(
        name="goal_decomposition_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are a text analytics task planner. 
        Users have collected a dataset of documents. The user will describe a goal to achieve through some text analytics, and what they have done already.
        ** Task **
        Your task is to provide a single next step based on what the user have done so far and the remaining steps to finish the task.
        Your task is to provide a single next step based on what the user have done so far and the remaining steps to finish the task.
        ** Requirements **
        Please specify the logical next step to take.
        The name of the step should be one concise noun-phrase.
        Ignore the practical steps such as data collection, cleaning or visualization.
        Focus on the conceptual next step. If no further steps are needed, label the next step with "END".
        For the parentIds, provide the ids of the steps that this step **directly** depends on in terms of input-output data.
        You should reply with {n} possible alternatives, so the user can have more choices.
        The alternatives should have varying complexity, coherence with previous steps, and importance.
        Reply with this JSON format. Do not wrap the json codes in JSON markers. Do not include any comments.
            {{
                "next_steps": [
                    {{
                        "label": (string) name of the step or "END 
        You should reply with {n} different next steps, so the user can have more choices.
        The different steps should have varying complexity, coherence with previous steps, and importance.
        Reply with this JSON format. Do not wrap the json codes in JSON markers.
            {{
                "next_steps": [
                    {{
                        "label": (string) or "END"
                        "description": (string)
                        "explanation": (string, explain why this step is needed)
                        "parentIds": (string[], ids of the steps that this step **directly** depends on)
                    }}
                    ... ({n} different next steps)
                    ],
            }}""".format(
            n=n
        ),
    )
    user_message = "My goal is: {goal}".format(goal=goal) + "\n"
    user_message += "There are {remaining_steps} steps remaining until you have to finish the task.\n".format(
        remaining_steps=remain_steps
    )
    user_message += "There are {remaining_steps} steps remaining until you have to finish the task.\n".format(
        remaining_steps=remain_steps
    )
    if len(previous_steps) > 0:
        previous_steps_str = "\n".join(
            list(
                map(
                    lambda s: f"""
                    <step>
                        <id> {s['id']} </id>
                        <label> {s['label']} </label>
                        <description> {s['description']} </description>
                    </step>""",
                    previous_steps,
                )
            )
        )
        user_message += (
            "Here are the steps that I have done so far: \n{previous_steps}".format(
                previous_steps=previous_steps_str
            )
        )

    response = await goal_decomposition_agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )

    retries, max_retries = 0, 5
    while True:
        try:
            response = extract_json_content(response.chat_message.content)["next_steps"]
            break
        except json.JSONDecodeError:
            print(f"Retrying... {retries}/{max_retries}-{retries > max_retries}")
            print(response.chat_message.content)
            if retries > max_retries:
                break
            response = await goal_decomposition_agent.on_messages(
                [TextMessage(content=user_message, source="user")],
                cancellation_token=CancellationToken(),
            )
            retries += 1
    return response
    # return extract_json_content(response.chat_message.content)["next_steps"]
    # if n == 1:
    #     response = await goal_decomposition_agent.on_messages(
    #         [TextMessage(content=user_message, source="user")],
    #         cancellation_token=CancellationToken(),
    #     )
    #     return extract_json_content(response.chat_message.content)["next_step"]
    # else:
    #     responses = await parallel_call_agents(
    #         n, goal_decomposition_agent, user_message
    #     )
    #     for index, response in enumerate(responses):
    #         retries, max_retries = 0, 5
    #         while True:
    #             try:
    #                 # print("Valid JSON:")
    #                 # print(response.chat_message.content)
    #                 response = extract_json_content(response.chat_message.content)["next_step"]
    #                 break
    #             except json.JSONDecodeError:
    #                 print(
    #                     f"Retrying... {retries}/{max_retries}-{retries > max_retries}"
    #                 )
    #                 print(response.chat_message.content)
    #                 if retries > max_retries:
    #                     break
    #                 response = await goal_decomposition_agent.on_messages(
    #                     [TextMessage(content=user_message, source="user")],
    #                     cancellation_token=CancellationToken(),
    #                 )
    #                 retries += 1
    #         responses[index] = response
    #     return responses

    response = await goal_decomposition_agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )

    retries, max_retries = 0, 5
    while True:
        try:
            response = json.loads(response.chat_message.content)["next_steps"]
            break
        except json.JSONDecodeError:
            print(f"Retrying... {retries}/{max_retries}-{retries > max_retries}")
            print(response.chat_message.content)
            if retries > max_retries:
                break
            response = await goal_decomposition_agent.on_messages(
                [TextMessage(content=user_message, source="user")],
                cancellation_token=CancellationToken(),
            )
            retries += 1
    return response
    # return json.loads(response.chat_message.content)["next_steps"]
    # if n == 1:
    #     response = await goal_decomposition_agent.on_messages(
    #         [TextMessage(content=user_message, source="user")],
    #         cancellation_token=CancellationToken(),
    #     )
    #     return json.loads(response.chat_message.content)["next_step"]
    # else:
    #     responses = await parallel_call_agents(
    #         n, goal_decomposition_agent, user_message
    #     )
    #     for index, response in enumerate(responses):
    #         retries, max_retries = 0, 5
    #         while True:
    #             try:
    #                 # print("Valid JSON:")
    #                 # print(response.chat_message.content)
    #                 response = json.loads(response.chat_message.content)["next_step"]
    #                 break
    #             except json.JSONDecodeError:
    #                 print(
    #                     f"Retrying... {retries}/{max_retries}-{retries > max_retries}"
    #                 )
    #                 print(response.chat_message.content)
    #                 if retries > max_retries:
    #                     break
    #                 response = await goal_decomposition_agent.on_messages(
    #                     [TextMessage(content=user_message, source="user")],
    #                     cancellation_token=CancellationToken(),
    #                 )
    #                 retries += 1
    #         responses[index] = response
    #     return responses


async def run_decomposition_self_evaluation_agent(
    goal: str, previous_steps: list, next_step: str, model: str, api_key: str, n=1
):
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    decomposition_self_evaluation_agent = AssistantAgent(
        name="decomposition_self_evaluation_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are a text analytics expert.
        Users will describe a text analytics goal and the steps they have taken to achieve it.
        ** Task **
        Your task is to evaluate the correctness of the next step provided by the user.
        ** Requirements **
        Give a score from 0 to 5, where 0 is completely incorrect and 5 is perfect.
        Reply with this JSON format:
            {
                "evaluation_score": (int) 0-5
            }  """,
    )
    user_message = "My goal is: {goal}".format(goal=goal) + "\n"
    if len(previous_steps) > 0:
        previous_steps_str = "\n".join(
            list(map(lambda s: f"{s['label']}: {s['description']}", previous_steps))
        )
        user_message += (
            "Here are the steps that I have done so far: \n{previous_steps}".format(
                previous_steps=previous_steps_str
            )
        )
    user_message += (
        "\nHere is the next step that I think I should take: {next_step}".format(
            next_step=next_step
        )
    )

    if n == 1:
        response = await decomposition_self_evaluation_agent.on_messages(
            [TextMessage(content=user_message, source="user")],
            cancellation_token=CancellationToken(),
        )
        return extract_json_content(response.chat_message.content)["evaluation_score"]
    else:
        responses = await parallel_call_agents(
            n, decomposition_self_evaluation_agent, user_message
        )
        responses = [
            extract_json_content(response.chat_message.content)["evaluation_score"]
            for response in responses
        ]
        return responses


async def run_decomposition_to_primitive_task_agent(
    tree: list[Node],
    primitive_task_list: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
) -> None:
    primitive_task_defs_str = ""
    for primitive_task in primitive_task_list:
        primitive_task_defs_str += "<primitive_task>\n"
        for key, value in primitive_task.items():
            primitive_task_defs_str += f"<{key}>{value}</{key}>\n"
        primitive_task_defs_str += "</primitive_task>\n"
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        response_format={"type": "json_object"},
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    decomposition_to_primitive_task_agent = AssistantAgent(
        name="decomposition_to_primitive_task_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are a Natural Language Processing (NLP) assistant. You are given a list of primitive NLP tasks that could be used.
        Here is the list of primitive NLP tasks:
        {primitive_task_defs}
        ** Task **
        The user will describe a series of real-world tasks for you. 
        For each of the task, decide if it can be formulated as an NLP task. If yes, you need to find the proper primitive NLP tasks and arrange them to accomplish user's goal. 
        You can ignore the need to handle formats or evaluate outputs.
        ** Requirements **
        The ids of each formulated NLP task must be unique, even if the labels are the same. This will help users correctly identify the dependent steps.
        If the same label appears multiple times, use the ids to differentiate them.
        For example, use 'Information Extraction-1' and 'Information Extraction-2' as ids.
        The label must be one of the primitive NLP tasks provided above.
        The labels of the primitive task must match exactly as those provided above. 
        Reply with the following JSON format: 
        {{ "primitive_tasks": [ 
                {{ 
                    "solves": (string) id of the user-provided task that this primitive task solves
                    "label": (string) (one of the NLP task labels above)
                    "id": (str) (a unique id for the task),
                    "description": (string, describe implementation procedure)
                    "explanation": (string, explain why this task is needed)
                    "depend_on": (str[], ids of the task that this step depends on)
                }}, 
                {{ 
                    "solves": (string) which user-provided task this primitive task solves
                    "label": (string) (one of the NLP task labels above)
                    "id": (str) (a unique id for the task),
                    "description": (string, describe implementation procedure)
                    "explanation": (string, explain why this task is needed)
                    "depend_on": (str[], ids of the task that this step depends on)
                }}, 
                ... 
            ] 
        }}
        """.format(
            primitive_task_defs=primitive_task_defs_str
        ),
    )
    task_to_string = (
        lambda _task: f"""
        <task>
            <id> {_task.id} </name>
            <name> {_task.label} </name>
            <description> {_task.description} <description>
            <depend_on> {_task.parentIds} </depend_on>
        </task>
        """
    )
    tree_str = "\n".join(list(map(task_to_string, tree)))

    user_message_content = """
    Here are my tasks: {tree_str}
    """.format(
        tree_str=tree_str
    )
    response = await decomposition_to_primitive_task_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )
    return extract_json_content(response.chat_message.content)["primitive_tasks"]


async def run_task_decomposition_agent(task: Node, model: str, api_key: str):
    # Create a countdown agent.
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    goal_decomposition_agent = AssistantAgent(
        name="task_decomposition_agent",
        model_client=model_client,
        system_message="""You are a text analytics task planner. 
        The use will describe a task to you, you need to help them decompose the task into subtasks. 
        Ignore the other practical parts such as data collection, cleaning or visualization.
        Focus on the conceptual steps that are needed to complete the task, with as few steps as possible.
        Reply with this JSON format: 
        { "steps": [ 
                { 
                    "id": int,
                    "label": (string) 
                    "description": (string) 
                    "explanation": (string, explain why this step is needed)
                    "depend_on": (int[], ids of the steps that this step depends on)
                }, 
                { 
                    "id": int,
                    "label": (string) 
                    "description": (string) 
                    "explanation": (string, explain why this step is needed)
                    "depend_on": (int[], ids of the steps that this step depends on)
                }, 
                ... 
            ] 
        }""",
    )
    user_message_content = task["label"] + ": " + task["description"]
    response = await goal_decomposition_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )
    return extract_json_content(response.chat_message.content)["steps"]


async def _run_decomposition_to_primitive_task_agent(
    task: Node,
    done_tasks: list[Node],
    primitive_task_list: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
) -> None:
    primitive_task_defs_str = ""
    for primitive_task in primitive_task_list:
        primitive_task_defs_str += "<primitive_task>\n"
        for key, value in primitive_task.items():
            primitive_task_defs_str += f"<{key}>{value}</{key}>\n"
        primitive_task_defs_str += "</primitive_task>\n"
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        response_format={"type": "json_object"},
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    decomposition_to_primitive_task_agent = AssistantAgent(
        name="decomposition_to_primitive_task_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are a Natural Language Processing (NLP) assistant. You are given a list of primitive NLP tasks that could be used.
        Here is the list of primitive NLP tasks:
        {primitive_task_defs}
        ** Task **
        The user will describe a series of real-world tasks for you. The user might have completed some of the tasks already, but they need help with a following task.
        The target task will be specified with <target_task> tags.
        First, decide if the target task can be formulated as an NLP task. If yes, you need to find the proper primitive NLP tasks and arrange them to accomplish user's goal. 
        If not, return "N/A".
        You can ignore the need to handle formats or evaluate outputs.
        ** Requirements **
        You only need to consider the target task.
        The ids of each formulated NLP task must be unique, even if the labels are the same. This will help users correctly identify the dependent steps.
        The labels of the primitive task must match exactly as those provided above. 
        Reply with the following JSON format: 
        {{ "primitive_tasks": [ 
                {{ 
                    "label": (string) (one of the NLP task labels above)
                    "id": (str) (a unique id for the task),
                    "description": (string, describe implementation procedure)
                    "explanation": (string, explain why this task is needed)
                    "depend_on": (str[], ids of the task that this step depends on)
                }}, 
                {{ 
                    "label": (string) (one of the NLP task labels above)
                    "id": (str) (a unique id for the task),
                    "description": (string, describe implementation procedure)
                    "explanation": (string, explain why this task is needed)
                    "depend_on": (str[], ids of the task that this step depends on)
                }}, 
                ... 
            ] 
        }}
        """.format(
            primitive_task_defs=primitive_task_defs_str
        ),
    )
    task_to_string = (
        lambda _task: f"""
        <target_task>
            <name> {_task.label} </name>
            <description> {_task.description} <description>
        </target_task
        """
    )
    user_message_content = """
    I have done the following tasks: {done_tasks}
    I want to know if and how this task can be formulated as one or more NLP task: {task}
    """.format(
        # list_of_tasks=list(map(lambda t: t.label, tree)),
        done_tasks="\n".join(map(lambda t: t.label, done_tasks)),
        task=task_to_string(task),
    )
    response = await decomposition_to_primitive_task_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )
    return extract_json_content(response.chat_message.content)["primitive_tasks"]


async def run_prompt_generation_agent(
    task: Node, existing_keys: str, model: str, api_key: str
):
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    prompt_generation_agent = AssistantAgent(
        name="prompt_generation_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in writing prompts for Large Language Models, especially for generating prompts that analyze a given piece of text.
        ** Task **
        The user will describe the task and provide a piece of text. You need to generate a prompt that can be used to analyze the text for the given task.
        ** Requirements **
        First, decide what data in each document is needed to complete the task.
        Here are the data already exist on each document, with type and schema: {existing_keys}
        Then, generate a prompt that instructs an LLM to analyze the text using the data in each document for the user's task.
        Organize the prompt into these three sections:
        1. Input Keys: List the keys that are required from the document to complete the task.
        2. Context: Give instructions on what the user is trying to do.
        3. Task: Give instructions on how to analyze the text.
        4. Requirements: Provide any specific requirements or constraints for the prompt.
        In addition, give a key name suitable to store the result of the prompt, and define a valid JSON format for the output.
        The output JSON format should be a dictionary with only one key, and the value can be any structure.
        Reply with this JSON format:
            {{
               "prompt": {{
                    "Context": str,
                    "Task": str,
                    "Requirements": str
                    "JSON_format": str
                }}
            }}
        """.format(
            existing_keys=existing_keys
        ),
    )
    task_message = f"""
        <task_name> {task['label']} </task_name>
        <description> {task['description']} </description>
        <explanation> {task['explanation']} </explanation>
    """
    response = await prompt_generation_agent.on_messages(
        [TextMessage(content=task_message, source="user")],
        cancellation_token=CancellationToken(),
    )
    # save_json(
    #     extract_json_content(response.chat_message.content),
    #     f"generated_prompt_{task['label']}.json",
    # )
    return extract_json_content(response.chat_message.content)["prompt"]


async def run_input_key_generation_agent(
    task: Node, existing_keys: str, model: str, api_key: str
):
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    prompt_generation_agent = AssistantAgent(
        name="input_key_generation_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in data schema design and text analytics.
        ** Task **
        The user will describe a task for you, and what data is available in the dataset. Your task is to pick the keys that are required from the dataset to complete the task, along with their detailed schema definition.
        ** Requirements **
        Reply with this JSON format:
            {
               "required_keys": [
                   {
                       "key": str,  // The name of the required key
                       "schema": str or object  // Detailed schema definition of the data structure
                   }
               ]
            }
        
        For each key, provide a detailed schema definition that describes the exact structure
        
        For primitive types, the schema can be the same as the type:
        - "schema": "str" for a string
        - "schema": "int" for an integer
        - "schema": "float" for a floating point number
        - "schema": "bool" for a boolean
        
        For complex types, the schema should define the structure:
        - For a list of strings: "schema": "list[str]"
        - For a list of objects: "schema": {"items": {"field1": "str", "field2": "int"}}
        - For a dictionary: "schema": {"properties": {"key1": "str", "key2": "int"}}
        
        Examples of schema definitions:
        1. Simple text content:
           {"key": "content", "schema": "str"}
           
        2. A list of tags:
           {"key": "tags", "schema": "list[str]"}
           
        3. A person record:
           {"key": "person", "schema": {"properties": {"name": "str", "age": "int", "email": "str"}}}
           
        4. A collection of documents:
           {"key": "documents", "schema": {"items": {"content": "str", "timestamp": "str", "author": "str"}}}
           
        5. Analytics results:
           {"key": "stats", "schema": {"properties": {"total_count": "int", "average_score": "float", "categories": "list[str]"}}}
        """,
    )

    # Format the existing keys to include detailed schema information
    formatted_keys = []
    for key in existing_keys:
        if isinstance(key, dict):
            if "key" in key and "schema" in key:
                formatted_keys.append(f"{key['key']} (schema: {key['schema']})")
            elif "key" in key:
                formatted_keys.append(f"{key['key']} (schema: str)") # default to use str for prompt tools
        elif isinstance(key, str):
            formatted_keys.append(f"{key} (schema: str)")

    existing_keys_str = ", ".join(formatted_keys) if formatted_keys else str(existing_keys)

    task_message = f"""
        <task_name> {task['label']} </task_name>
        <description> {task['description']} </description>
        <explanation> {task['explanation']} </explanation>
        <existing_keys> {existing_keys_str} </existing_keys>
        
        Please provide detailed schema definitions for each key, not just basic types. 
        For complex structures, define the exact fields and their types in the schema.
    """
    response = await prompt_generation_agent.on_messages(
        [TextMessage(content=task_message, source="user")],
        cancellation_token=CancellationToken(),
    )
    return extract_json_content(response.chat_message.content)["required_keys"]


async def run_result_evaluator_generation_agent(
    task,
    user_description: str,
    model: str,
    api_key: str,
):
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=1.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    # ** Requirements **
    # The JSON format should match the unit that the user wants to evaluate.
    # Reply the evaluator specification with this JSON format. Do not wrap the json codes in JSON markers. Do not include any comments.
    # Wrap the types of the values in the JSON format with single quotes.
    prompt_generation_agent = AssistantAgent(
        name="input_key_generation_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in generating LLM judges. An LLM judge is an agent that can generate a score using some criteria.
        ** Task **
        The user will describe a text analysis task that he/she has done on a list of documents, and how he/she wants the llm judge to evaluate the task result of each document. Your task is to generate a specification of the LLM judge.
        The LLM judge should do the following:
            First, identify what the user wants to evaluate on each document. 
            Then, for each document, output a categorical score using the user-specified criteria.
        ** Requirements **
        In the LLM judge's prompt template, specify that the LLM judge must generate only **ONE** score for each document.
        Reply the evaluator specification with this JSON format. Do not wrap the json codes in JSON markers. Do not include any comments.
            {{
                "evaluator_specification": {{
                    "name": str,
                    "definition": str,
                    "prompt_template": {{
                            "Context": str,
                            "Task": str,
                            "Possible Scores": list[str]
                    }}
                }}
            }}
        """,
    )
    task_message = f"""
        <task_name> {task['label']} </task_name>
        <description> {task['description']} </description>
    """
    user_message = "This is what I have done: " + task_message + "\n"
    user_message += "Here's what I want to evaluate: " + user_description
    response = await prompt_generation_agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )
    print(response.chat_message.content)
    return extract_json_content(response.chat_message.content)[
        "evaluator_specification"
    ]


async def run_data_transform_plan_agent(
    task: Node, existing_keys: str, model: str, api_key: str
):
    """
    Generate a data transformation plan for a task using an agent.

    Args:
        task: The task node
        existing_keys: Keys available for input with their detailed schemas
        model: The model to use
        api_key: The API key for the model

    Returns:
        A data transformation plan
    """
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    data_transform_agent = AssistantAgent(
        name="data_transform_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating data transformation plans for document processing.
        You will create a plan for transforming input data from one schema to another based on the task description.
        
        ** Task **
        The user will describe a data transformation task. You need to create a transformation plan
        that includes the operation type, the required parameters for that operation, and the output schema.

        ** Note **
        The input data may have complex schemas with nested structures. You must create transformations 
        that account for the detailed schema of the input data and define a precise output schema.

        ** IMPORTANT: Available Operations **
        You MUST choose ONE of these operations - no other operations are supported:
        
        1. map - Transforms each document by applying a template
           - Required parameters: 
              - "template": A jinja2 compatible template string
              - "output_schema": Detailed schema of the output structure
           - You should handle complex schema structures appropriately in the template.
           - Example: To map input data with a person schema to a new format:
            ```
            // Input schema: {"properties": {"first_name": "str", "last_name": "str", "dob": "str", "salary": "int", "skills": "list[str]"}}
            
            "template": {
                "name": "{{first_name}} {{last_name}}",
                "birth_year": {{dob.split('-')[0]}},
                "tax": {{round(salary * 0.3, 2)}},
                "is_senior": {{ True if age >= 65 else False }},
                "skills_summary": "{{', '.join(skills)}}" if skills is defined and skills|length > 0 else "None",
                "contact_info": {
                    "email": "{{email | default('unknown')}}",
                    "phones": {{phone_numbers if phone_numbers is defined else []}}
                }
            },
            "output_schema": {
                "properties": {
                    "name": "str", 
                    "birth_year": "int", 
                    "tax": "float", 
                    "is_senior": "bool",
                    "skills_summary": "str",
                    "contact_info": {
                        "properties": {
                            "email": "str",
                            "phones": "list[str]"
                        }
                    }
                }
            }
            ```

        2. filter - Selects documents that meet specific criteria
           - Required parameters: 
              - "filter_code": Python code that defines a filter_data function
              - "output_schema": Schema of the output (same as input typically)
           - The function must:
             - Be named "filter_data"
             - Take a "data" parameter (list of documents)
             - Return filtered data
           - Your code should handle complex schema structures when filtering.
           - Example: to filter documents with complex criteria:
```
// Input schema: {"items": {"name": "str", "department": "str", "salary": "int", "skills": "list[str]", "experience": {"properties": {"years": "int", "level": "str"}}}}

"filter_code": "def filter_data(data):\n    filtered = []\n    for item in data:\n        salary_in_range = item.get('salary', 0) >= 80000\n        if salary_in_range:\n            filtered.append(item)\n    return filtered",

"output_schema": {"items": {"name": "str", "department": "str", "salary": "int", "skills": "list[str]", "experience": {"properties": {"years": "int", "level": "str"}}}}
```
        
        3. reduce - Combines multiple documents into a single result
           - Required parameters: 
              - "reduce_code": Python code that defines a reduce_data function
              - "output_schema": Detailed schema of the output structure
           - The function must:
             - Be named "reduce_data"
             - Take a "data" parameter (list of documents)
             - Return the reduced result as a dictionary
           - Example: to reduce documents to a complex aggregated result:
```
// Input schema: {"items": {"name": "str", "department": "str", "salary": "int", "skills": "list[str]"}}

"reduce_code": "def reduce_data(data):\n    total_salary = sum(item.get('salary', 0) for item in data)\n    avg_salary = total_salary / len(data) if data else 0\n    return {\n        \"summary\": {\n            \"total_employees\": len(data),\n            \"total_salary\": total_salary,\n            \"average_salary\": avg_salary\n        }\n    }"

"output_schema": {
    "summary": {
        "properties": {
            "total_employees": "int",
            "total_salary": "int",
            "average_salary": "float"
        }
    }
}
```
        4. chain - Applies multiple transformations in sequence
           - Parameters:
             - "map_config": Configuration for map operation (can be null)
             - "filter_config": Configuration for filter operation (can be null)
             - "reduce_config": Configuration for reduce operation (can be null)
             - "output_schema": Final output schema after all transformations
        
        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "operation": "map" | "filter" | "reduce" | "chain",
            "parameters": {
                // Parameters specific to the chosen operation as described above,
                // MUST include output_schema defining the exact structure of the output
            }
        }
        """,
    )

    # Format input keys with their detailed schema information
    input_keys_info = []
    for key in existing_keys:
        if isinstance(key, dict):
            if "key" in key and "schema" in key:
                input_keys_info.append(f"{key['key']} (schema: {key['schema']})")
            elif "key" in key and "type" in key:
                input_keys_info.append(f"{key['key']} (type: {key['type']})")
        elif isinstance(key, str):
            input_keys_info.append(f"{key} (type: any)")

    input_keys_str = ", ".join(input_keys_info) if input_keys_info else "None"

    user_message_content = f"""
    I need to create a data transformation for the following task:
    
    Task: {task['label']}
    Description: {task['description']}
    
    Available input keys with their detailed schemas: {input_keys_str}
    
    Please generate a data transformation plan that best addresses this task. 
    Remember to:
    1. Choose only one of the available operations (map, filter, reduce, or chain)
    2. Include all required parameters including a detailed output_schema
    3. Consider the detailed schemas of input keys when creating transformations
    4. Define precise schemas for all output data structures
    """

    response = await data_transform_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )

    return extract_json_content(response.chat_message.content)


async def run_clustering_plan_agent(
    task: Node, existing_keys: str, model: str, api_key: str
):
    """
    Generate a clustering plan for a task using an agent.

    Args:
        task: The task node
        existing_keys: Keys available for input with their detailed schemas
        model: The model to use
        api_key: The API key for the model

    Returns:
        A clustering plan configuration
    """
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    clustering_agent = AssistantAgent(
        name="clustering_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating clustering plans for document analysis.
        You will create a configuration for clustering documents based on the task description.
        
        ** Task **
        The user will describe a clustering task. You need to create a clustering configuration
        that includes the algorithm to use and the parameters for that algorithm.

        ** Note **
        The input data needs to contain embeddings (vector representations) for effective clustering.
        You need to specify which feature to use for clustering (typically "embedding").

        ** IMPORTANT: Available Clustering Algorithms **
        Choose ONE of these algorithms based on the task requirements:
        
        1. kmeans - K-means clustering (requires number of clusters)
           - Good for: Simple clustering with roughly equal-sized, well-separated clusters
           - Parameters:
             - n_clusters: Number of clusters (required, integer)
             - init: Initialization method ('k-means++' or 'random')
             - n_init: Number of initializations to try
             - max_iter: Maximum number of iterations
        
        2. dbscan - Density-Based Spatial Clustering (doesn't require number of clusters)
           - Good for: Finding clusters of arbitrary shape, handling noise/outliers
           - Parameters:
             - eps: Maximum distance between samples for neighborhood
             - min_samples: Minimum number of samples in a neighborhood
             - metric: Distance metric to use
        
        3. agglomerative - Hierarchical clustering
           - Good for: Finding hierarchical relationships, generating dendrograms
           - Parameters:
             - n_clusters: Number of clusters (required, integer)
             - linkage: Linkage criterion ('ward', 'complete', 'average', or 'single')
             - affinity: Distance metric to use
        
        4. gaussian_mixture - Gaussian Mixture Model
           - Good for: Soft clustering with probability distributions
           - Parameters:
             - n_components: Number of mixture components (required, integer)
             - covariance_type: Type of covariance ('full', 'tied', 'diag', 'spherical')
             - max_iter: Maximum number of iterations
        
        5. hdbscan - Hierarchical DBSCAN
           - Good for: Finding clusters of varying densities, robust to noise
           - Parameters:
             - min_cluster_size: Minimum size for a cluster
             - min_samples: Minimum number of samples in neighborhood
             - cluster_selection_epsilon: Distance threshold for cluster formation
        
        6. bertopic - BERTopic (uses transformer models with UMAP+HDBSCAN)
           - Good for: Topic modeling and clustering of text documents
           - Parameters:
             - min_topic_size: Minimum size for a topic
             - n_neighbors: Number of neighbors for UMAP
             - low_memory: Lower memory usage but slower (True/False)

        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "algorithm": "kmeans" | "dbscan" | "agglomerative" | "gaussian_mixture" | "hdbscan" | "bertopic",
            "parameters": {
                // Parameters specific to the chosen algorithm
                "feature_key": str,  // Feature to use for clustering (e.g., "embedding")
                // Additional algorithm-specific parameters
            },
            "output_schema": {
                // Schema of the output data
                // For standard output (return_metrics=False):
                "labels": "list[int]"
            }
        }
        """,
    )

    # Format input keys with their detailed schema information
    input_keys_info = []
    for key in existing_keys:
        if isinstance(key, dict):
            if "key" in key and "schema" in key:
                input_keys_info.append(f"{key['key']} (schema: {key['schema']})")
            elif "key" in key and "type" in key:
                input_keys_info.append(f"{key['key']} (type: {key['type']})")
        elif isinstance(key, str):
            input_keys_info.append(f"{key} (type: any)")

    input_keys_str = ", ".join(input_keys_info) if input_keys_info else "None"

    user_message_content = f"""
    I need to create a clustering plan for the following task:
    
    Task: {task['label']}
    Description: {task['description']}
    
    Available input keys with their detailed schemas: {input_keys_str}
    
    Please generate a clustering configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate clustering algorithm for the task
    2. Specify all required parameters for that algorithm
    3. Identify which feature to use for clustering (typically "embedding")
    4. Decide if evaluation metrics should be returned
    5. Define the output schema
    """

    response = await clustering_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )

    return extract_json_content(response.chat_message.content)


async def run_dim_reduction_plan_agent(
    task: Node, existing_keys: str, model: str, api_key: str
):
    """
    Generate a dimensionality reduction plan for a task using an agent.

    Args:
        task: The task node
        existing_keys: Keys available for input with their detailed schemas
        model: The model to use
        api_key: The API key for the model

    Returns:
        A dimensionality reduction plan configuration
    """
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    dim_reduction_agent = AssistantAgent(
        name="dim_reduction_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating dimensionality reduction plans for data visualization and analysis.
        You will create a configuration for reducing the dimensions of data based on the task description.
        
        ** Task **
        The user will describe a dimensionality reduction task. You need to create a configuration
        that includes the algorithm to use and the parameters for that algorithm.

        ** Note **
        The input data needs to contain high-dimensional embeddings that need to be reduced to lower dimensions.
        You need to specify which feature to use (typically "embedding") and the number of dimensions to reduce to.

        ** IMPORTANT: Available Dimensionality Reduction Algorithms **
        Choose ONE of these algorithms based on the task requirements:
        
        1. pca - Principal Component Analysis
           - Good for: Linear dimensionality reduction, preserving global structure
           - Fast, but may not capture non-linear relationships
           - Parameters:
             - n_components: Number of dimensions to reduce to (required, integer)
             - whiten: Whether to whiten the data (boolean)
        
        2. tsne - t-distributed Stochastic Neighbor Embedding
           - Good for: Non-linear dimensionality reduction, preserving local structure
           - Better for visualization but computationally intensive
           - Parameters:
             - n_components: Number of dimensions to reduce to (required, integer)
             - perplexity: Related to number of nearest neighbors (default 30)
             - early_exaggeration: Control early clustering (default 12)
             - learning_rate: Learning rate (default 200)
        
        3. umap - Uniform Manifold Approximation and Projection
           - Good for: Non-linear dimensionality reduction with better global structure than t-SNE
           - Fast and effective for visualization and machine learning
           - Parameters:
             - n_components: Number of dimensions to reduce to (required, integer)
             - n_neighbors: Size of local neighborhood (default 15)
             - min_dist: Minimum distance between points (default 0.1)
             - metric: Distance metric to use (default 'euclidean')

        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "algorithm": "pca" | "tsne" | "umap",
            "parameters": {
                "feature_key": str,  // Feature to use for dimension reduction (e.g., "embedding")
                "n_components": int,  // Number of dimensions to reduce to (typically 2 or 3 for visualization)
                // Additional algorithm-specific parameters
            },
            "output_schema": {
                // Schema of the output data
                "properties": {
                    "reduced_dimensions": "list[list[float]]"  // Each inner list is a point in lower-dimensional space
                }
            }
        }
        """,
    )

    # Format input keys with their detailed schema information
    input_keys_info = []
    for key in existing_keys:
        if isinstance(key, dict):
            if "key" in key and "schema" in key:
                input_keys_info.append(f"{key['key']} (schema: {key['schema']})")
            elif "key" in key and "type" in key:
                input_keys_info.append(f"{key['key']} (type: {key['type']})")
        elif isinstance(key, str):
            input_keys_info.append(f"{key} (type: any)")

    input_keys_str = ", ".join(input_keys_info) if input_keys_info else "None"

    user_message_content = f"""
    I need to create a dimensionality reduction plan for the following task:
    
    Task: {task['label']}
    Description: {task['description']}
    
    Available input keys with their detailed schemas: {input_keys_str}
    
    Please generate a dimensionality reduction configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate dimensionality reduction algorithm for the task
    2. Specify all required parameters for that algorithm
    3. Identify which feature to use (typically "embedding")
    4. Define the number of components to reduce to
    5. Define the output schema
    """

    response = await dim_reduction_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )

    return extract_json_content(response.chat_message.content)


async def run_embedding_plan_agent(
    task: Node, existing_keys: str, model: str, api_key: str
):
    """
    Generate an embedding plan for a task using an agent.

    Args:
        task: The task node
        existing_keys: Keys available for input with their detailed schemas
        model: The model to use
        api_key: The API key for the model

    Returns:
        An embedding plan configuration
    """
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    embedding_agent = AssistantAgent(
        name="embedding_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating embedding plans for text data.
        You will create a configuration for generating vector embeddings based on the task description.
        
        ** Task **
        The user will describe an embedding task. You need to create a configuration
        that includes the embedding model to use and the parameters for that model.

        ** Note **
        Embeddings convert text into dense vector representations that capture semantic meaning.
        You need to specify which text field to embed (typically "content") and which embedding model to use.

        ** IMPORTANT: Available Embedding Providers and Models **
        Choose a provider and model combination based on the task requirements:
        
        1. openai - OpenAI's embedding models
           - Models: "text-embedding-ada-002" (default), "text-embedding-3-small", "text-embedding-3-large"
           - Good for: High-quality embeddings, semantic search, clustering
           - Requires API key
           - Parameters:
             - feature_key: The field containing text to embed (required, string)
             - model: The embedding model to use (string)
        
        2. sentence_transformers - Local embedding models using Sentence Transformers
           - Models: "all-MiniLM-L6-v2" (default), "all-mpnet-base-v2", "paraphrase-multilingual-MiniLM-L12-v2"
           - Good for: Local processing without API calls, multilingual support
           - No API key required
           - Parameters:
             - feature_key: The field containing text to embed (required, string)
             - model: The embedding model to use (string)

        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "provider": "openai" | "sentence_transformers",
            "parameters": {
                "feature_key": str,  // Text field to embed (e.g., "content")
                "model": str,  // Embedding model to use
                // Any additional parameters specific to the provider
            },
            "output_schema": {
                // Schema of the output embeddings
                "embedding": "list[float]"  // Vector representation as a list of floats
            }
        }
        """,
    )

    # Format input keys with their detailed schema information
    input_keys_info = []
    for key in existing_keys:
        if isinstance(key, dict):
            if "key" in key and "schema" in key:
                input_keys_info.append(f"{key['key']} (schema: {key['schema']})")
            elif "key" in key and "type" in key:
                input_keys_info.append(f"{key['key']} (type: {key['type']})")
        elif isinstance(key, str):
            input_keys_info.append(f"{key} (type: any)")

    input_keys_str = ", ".join(input_keys_info) if input_keys_info else "None"

    user_message_content = f"""
    I need to create an embedding plan for the following task:
    
    Task: {task['label']}
    Description: {task['description']}
    
    Available input keys with their detailed schemas: {input_keys_str}
    
    Please generate an embedding configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate embedding provider for the task
    2. Select a suitable embedding model
    3. Identify which feature to use as input text (typically "content")
    4. Define the output schema for the embeddings
    5. Consider whether API access is available or if local processing is needed
    """

    response = await embedding_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )

    return extract_json_content(response.chat_message.content)


async def run_segmentation_plan_agent(
    task: Node, existing_keys: str, model: str, api_key: str
):
    """
    Generate a segmentation plan for a task using an agent.

    Args:
        task: The task node
        existing_keys: Keys available for input with their detailed schemas
        model: The model to use
        api_key: The API key for the model

    Returns:
        A segmentation plan configuration
    """
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": True,
        },
    )
    segmentation_agent = AssistantAgent(
        name="segmentation_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in text segmentation for document processing.
        You will create a configuration for segmenting text documents based on the task description.
        
        ** Task **
        The user will describe a segmentation task. You need to create a configuration
        that includes the segmentation strategy and the parameters for that strategy.

        ** Note **
        Text segmentation divides long documents into smaller, manageable chunks.
        You need to specify which text field to segment and how to divide it.

        ** IMPORTANT: Available Segmentation Strategies **
        Choose ONE of these strategies based on the task requirements:
        
        1. paragraph - Split text by paragraphs
           - Good for: Natural document structure, preserving paragraph meaning
           - Simple and effective for well-formatted documents
           - Parameters:
             - content_key: The field containing text to segment (required, string)
             - output_key: Field name for storing segments (default: "segments")
        
        2. sentence - Split text by sentences
           - Good for: Fine-grained analysis, shorter segments
           - Uses NLTK's sentence tokenizer
           - Parameters:
             - content_key: The field containing text to segment (required, string)
             - output_key: Field name for storing segments (default: "segments")
        
        3. fixed_length - Split text into chunks of specified length
           - Good for: Creating uniform-sized chunks
           - Allows for overlapping chunks to preserve context
           - Parameters:
             - content_key: The field containing text to segment (required, string)
             - output_key: Field name for storing segments (default: "segments")
             - chunk_size: Maximum number of characters per chunk (default: 100)
             - overlap: Number of overlapping characters between chunks (default: 10)
        
        4. semantic - Split text based on semantic meaning
           - Good for: Creating semantically coherent chunks
           - Uses embeddings to detect topic shifts
           - Parameters:
             - content_key: The field containing text to segment (required, string)
             - output_key: Field name for storing segments (default: "segments")
             - threshold: Similarity threshold for boundary detection (default: 0.5)
             - model: Optional model to use for embeddings (default: depends on availability)
             - api_key: API key for embedding model (if required)

        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "strategy": "paragraph" | "sentence" | "fixed_length" | "semantic",
            "parameters": {
                "content_key": str,  // Text field to segment (e.g., "content")
                "output_key": str,   // Field name for storing segments (e.g., "segments")
                // Additional strategy-specific parameters
            },
            "output_schema": {
                // Schema of the output segments
                "properties": {
                    "segments": "list[str]"  // List of text segments
                }
            }
        }
        """,
    )

    # Format input keys with their detailed schema information
    input_keys_info = []
    for key in existing_keys:
        if isinstance(key, dict):
            if "key" in key and "schema" in key:
                input_keys_info.append(f"{key['key']} (schema: {key['schema']})")
            elif "key" in key and "type" in key:
                input_keys_info.append(f"{key['key']} (type: {key['type']})")
        elif isinstance(key, str):
            input_keys_info.append(f"{key} (type: any)")

    input_keys_str = ", ".join(input_keys_info) if input_keys_info else "None"

    user_message_content = f"""
    I need to create a segmentation plan for the following task:
    
    Task: {task['label']}
    Description: {task['description']}
    
    Available input keys with their detailed schemas: {input_keys_str}
    
    Please generate a segmentation configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate segmentation strategy for the task
    2. Specify all required parameters for that strategy
    3. Identify which feature to use as input text (typically "content")
    4. Define the output key where segments will be stored
    5. Define the output schema for the segments
    """

    response = await segmentation_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )

    return extract_json_content(response.chat_message.content)