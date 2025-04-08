import os
import re
import yaml
from typing import List, Literal

from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
from autogen_core.models import ModelFamily
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.anthropic import (
    AnthropicChatCompletion,
    AnthropicChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.google.google_ai import (
    GoogleAIChatCompletion,
    GoogleAIChatPromptExecutionSettings,
)
from semantic_kernel.memory.null_memory import NullMemory

from dotenv import load_dotenv

load_dotenv("../../.env")
dirname = os.path.dirname(__file__)
relative_path = lambda filename: os.path.join(dirname, filename)

AnthropicModelType = Literal[
    "claude-3-haiku",
    "claude-3-sonnet",
    "claude-3-opus",
    "claude-3.5-haiku",
    "claude-3.5-sonnet",
]

GeminiModelType = Literal["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]


def get_openai_client(model_name: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY is not set")

    return OpenAIChatCompletionClient(model=model_name, api_key=api_key)


def get_claude_client(model_name: str):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    sk_client = AnthropicChatCompletion(ai_model_id=model_name, api_key=api_key)
    settings = AnthropicChatPromptExecutionSettings(
        temperature=0.0,
    )

    model_family_mapping = [
        (r"claude-3[._-]5-sonnet", ModelFamily.CLAUDE_3_5_SONNET),
        (r"claude-3[._-]5-haiku", ModelFamily.CLAUDE_3_5_HAIKU),
        ("claude-3-opus", ModelFamily.CLAUDE_3_OPUS),
        ("claude-3-sonnet", ModelFamily.CLAUDE_3_SONNET),
        ("claude-3-haiku", ModelFamily.CLAUDE_3_HAIKU),
    ]

    family = None
    model_name_lower = model_name.lower()
    for pattern, model_family in model_family_mapping:
        if re.search(pattern, model_name_lower):
            family = model_family
            break

    if not family:
        return None

    return SKChatCompletionAdapter(
        sk_client,
        kernel=Kernel(memory=NullMemory()),
        prompt_settings=settings,
        model_info={
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "family": family,
        },
    )


def get_gemini_client(model_name: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    sk_client = GoogleAIChatCompletion(
        gemini_model_id=model_name,
        api_key=os.environ["GEMINI_API_KEY"],
    )
    settings = GoogleAIChatPromptExecutionSettings(
        temperature=0.0,
    )

    model_family_mapping = [
        (r"gemini-2[._-]0-flash", ModelFamily.GEMINI_2_0_FLASH),
        (r"gemini-1[._-]5-pro", ModelFamily.GEMINI_1_5_PRO),
        (r"gemini-1[._-]5-flash", ModelFamily.GEMINI_1_5_FLASH),
    ]

    family = None
    model_name_lower = model_name.lower()
    for pattern, model_family in model_family_mapping:
        if re.search(pattern, model_name_lower):
            family = model_family
            break

    if not family:
        return None

    return SKChatCompletionAdapter(
        sk_client,
        kernel=Kernel(memory=NullMemory()),
        prompt_settings=settings,
        model_info={
            "function_calling": True,
            "json_output": True,
            "vision": True,
            "family": family,
        },
    )


def get_agents(agent_name: str, system_message: str):
    with open(relative_path("model_list.yaml"), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        model_list = data.get("eval-models", [])

    agents = []

    for model in model_list:
        if model.startswith(("gpt-", "chatgpt-", "o1-")):
            model_client = get_openai_client(model)
        elif model.startswith("claude-3-"):
            model_client = get_claude_client(model)
        elif model.startswith("gemini-"):
            model_client = get_gemini_client(model)
        else:
            model_client = None

        if model_client:
            agent = AssistantAgent(
                name=f"{model.replace('-', '_').replace('.', '_')}_{agent_name}",
                model_client=model_client,
                system_message=system_message,
            )
            agents.append((model, agent))

    return agents


async def get_response(agent: AssistantAgent, messages: List[TextMessage]):
    response = response = await agent.on_messages(
        messages,
        cancellation_token=CancellationToken(),
    )

    result_text = response.chat_message.content.strip()

    return result_text
