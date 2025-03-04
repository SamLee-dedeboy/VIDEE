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
                        "id": (string),
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
        Here are the data already exist on each document: {existing_keys}
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
        You are an expert in text analytics.
        ** Task **
        The user will describe a task for you, and what data is available in the dataset. Your task is to pick the keys that are required from the dataset to complete the task.
        ** Requirements **
        Reply with this JSON format:
            {{
               "required keys": str[]
            }}
        """,
    )
    task_message = f"""
        <task_name> {task['label']} </task_name>
        <description> {task['description']} </description>
        <explanation> {task['explanation']} </explanation>
        <existing_keys> {existing_keys} </existing_keys>
    """
    response = await prompt_generation_agent.on_messages(
        [TextMessage(content=task_message, source="user")],
        cancellation_token=CancellationToken(),
    )
    return extract_json_content(response.chat_message.content)["required keys"]


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
    prompt_generation_agent = AssistantAgent(
        name="input_key_generation_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in generating LLM judges. An LLM judge is an agent that can generate a score using some criteria.
        ** Task **
        The user will describe a task that he/she has done, and how he/she wants the llm judge to evaluate the task result. Your task is to generate a specification of the LLM judge.
        ** Requirements **
        Some requirements for the prompt_template:
            The possible scores should be categorical, like "Low", "Mid", "High".
            The JSON format should be a dictionary with only one key. Put the actual output format as the value of the key. The format (list or dict) should match the requirements of the user.
        Reply the evaluator specification with this JSON format:
            {{
                "evaluator_specification": {{
                    "name": str,
                    "definition": str,
                    "prompt_template": {{
                            "Context": str,
                            "Task": str,
                            "Possible Scores": list[str]
                            "JSON_format": str
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
    print(response)
    return extract_json_content(response.chat_message.content)[
        "evaluator_specification"
    ]
