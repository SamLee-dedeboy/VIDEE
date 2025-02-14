from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage

async def run_complexity_evaluation_agent(
    text: str,
    model: str,
    api_key: str,
    complexity_definition: str = (
        "A text is considered complex if it requires advanced knowledge "
        "or expertise, contains multiple layered or specialized concepts, or "
        "requires multi-step reasoning to understand or accomplish the described goal. "
        "Otherwise, it's considered not complex."
    ),
):
    
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
    )
    
    complexity_evaluation_agent = AssistantAgent(
        name="complexity_evaluation_agent",
        model_client=model_client,
        # temperature=0.5,
        system_message=f"""You are a text complexity evaluator. The user will provide some text that describes a task.
Your job is to evaluate whether the text is 'complex' or 'not complex' based on the following definition:
{complexity_definition}

If the text meets the complexity definition, respond with:
"Yes"

Otherwise, respond with:
"No"

Output must be EXACTLY one of these words, with no additional formatting, punctuation, or explanation.
""",
    )
    
    response = await complexity_evaluation_agent.on_messages(
        [TextMessage(content=text, source="user")],
        cancellation_token=CancellationToken(),
    )

    result = response.chat_message.content.strip()
    return 1 if result == "Yes" else 0


async def run_coherence_evaluation_agent(
    parent_part: str,
    child_part: str,
    model: str,
    api_key: str,
    coherence_definition: str = (
        "Two text pieces are considered coherent in a sequence if the second "
        "logically or thematically follows from the first, maintains consistency with it, "
        "and does not present a contradictory or unrelated concept."
    ),
):
    
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
    )
    
    coherence_evaluation_agent = AssistantAgent(
        name="coherence_evaluation_agent",
        model_client=model_client,
        # temperature=0.5,
        system_message=f"""You are a coherence evaluator. You will be given two parts of a sequence:
- Parent Part: {parent_part}
- Child Part: {child_part}

Evaluate whether Child Part logically or thematically follows from Parent Part, consistent with the following definition of coherence:
{coherence_definition}

If they are coherent, respond with:
"Yes"

If they are not coherent, respond with:
"No"

Output must be EXACTLY one of these words, with no additional formatting, punctuation, or explanation.
"""
    )
    
    response = await coherence_evaluation_agent.on_messages(
        [TextMessage(content="", source="user")],
        cancellation_token=CancellationToken(),
    )
    
    result = response.chat_message.content.strip()
    
    return 1 if result == "Yes" else 0


async def run_importance_evaluation_agent(
    final_goal: str,
    subtask_description: str,
    model: str,
    api_key: str,
    importance_definition: str = (
        "A subtask is considered important if it is critical, essential, "
        "or significantly beneficial to achieving the final goal. If it is tangential, "
        "optional, or has minimal impact, then it is not important."
    ),
):
    
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
    )
    
    importance_evaluation_agent = AssistantAgent(
        name="importance_evaluation_agent",
        model_client=model_client,
        # temperature=0.5,
        system_message=f"""You are an importance evaluator. You will be given:
- A final task goal: {final_goal}
- A subtask description: {subtask_description}

Evaluate whether the subtask is important using the following definition:
{importance_definition}

If they are important, respond with:
"Yes"

Otherwise, respond with:
"No"

Output must be EXACTLY one of these words, with no additional formatting, punctuation, or explanation.
""")
    
    response = await importance_evaluation_agent.on_messages(
        [TextMessage(content="", source="user")],
        cancellation_token=CancellationToken(),
    )
    
    result = response.chat_message.content.strip()
    return 1 if result == "Yes" else 0