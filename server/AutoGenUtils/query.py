import json
from server.custom_types import Node, PrimitiveTaskDescription
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage


async def run_goal_decomposition_agent(goal: str, model: str, api_key: str):
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
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
    return json.loads(response.chat_message.content)["steps"]


async def run_task_decomposition_agent(task: Node, model: str, api_key: str):
    # Create a countdown agent.
    model_client = OpenAIChatCompletionClient(
        model=model, api_key=api_key, temperature=0.0
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
    return json.loads(response.chat_message.content)["steps"]


async def run_decomposition_to_primitive_task_agent(
    task: Node,
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
        The user will describe a series of real-world tasks for you. First, for each of the task, decide if it can be formulated as an NLP task. If yes, you need to find the proper primitive NLP tasks and arrange them to accomplish user's goal. 
        You can ignore the need to handle formats or evaluate outputs.
        ** Requirements **
        The ids of each step must be unique, even if the labels are the same. This will help users correctly identify the dependent steps.
        The labels of the primitive task must match exactly as those provided above. 
        If the same label appears multiple times, use the ids to differentiate them.
        For example, use 'Information Extraction-1' and 'Information Extraction-2' as ids.
        The label must be one of the primitive NLP tasks provided above.
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
    user_message_content = json.dumps(tree)
    response = await decomposition_to_primitive_task_agent.on_messages(
        [TextMessage(content=user_message_content, source="user")],
        cancellation_token=CancellationToken(),
    )
    print(response.chat_message.content)
    return json.loads(response.chat_message.content)["primitive_tasks"]
