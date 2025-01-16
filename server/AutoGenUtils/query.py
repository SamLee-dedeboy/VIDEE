import json
from typing import AsyncGenerator, List, Sequence
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage


async def run_goal_decomposition_agent(goal: str) -> None:
    # Create a countdown agent.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=open("api_key").read(),
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
                        "label": (string)
                        "description": (string)
                        "explanation": (string, explain why this step is needed)
                        "depend_on": (string[], the steps that this step depends on)
                    },
                    {
                        "label": (string)
                        "description": (string)
                        "explanation": (string, explain why this step is needed)
                        "depend_on": (string[], the steps that this step depends on)
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


async def run_task_decomposition_agent(task) -> None:
    # Create a countdown agent.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=open("api_key").read(),
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
                    "label": (string) 
                    "description": (string) 
                    "explanation": (string, explain why this step is needed)
                    "depend_on": (string[], the steps that this step depends on)
                }, 
                { 
                    "label": (string) 
                    "description": (string) 
                    "explanation": (string, explain why this step is needed)
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
