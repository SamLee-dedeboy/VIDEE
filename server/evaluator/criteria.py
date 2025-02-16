from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from tqdm import tqdm
import asyncio
import itertools


# import json


# def save_json(data, filename):
#     with open(filename, "w") as f:
#         json.dump(data, f, indent=4, ensure_ascii=False)


async def run_all_evaluations(
    eval_params: list[tuple[str, str, str]],  # [goal, node_str, parent_node_str]
    eval_definitions: dict[str, str],
    model: str,
    api_key: str,
):
    """Run all evaluation agents for all nodes. Each node is evaluated for complexity, coherence, and importance."""
    nested_tasks = [
        [
            run_complexity_evaluation_agent(
                text=node_str,
                model=model,
                api_key=api_key,
                complexity_definition=eval_definitions["complexity"],
            ),
            run_coherence_evaluation_agent(
                parent_part=parent_node_str,
                child_part=node_str,
                model=model,
                api_key=api_key,
                coherence_definition=eval_definitions["coherence"],
            ),
            run_importance_evaluation_agent(
                final_goal=goal,
                subtask_description=node_str,
                model=model,
                api_key=api_key,
                importance_definition=eval_definitions["importance"],
            ),
        ]
        for goal, node_str, parent_node_str in eval_params
    ]
    tasks = list(itertools.chain(*nested_tasks))
    # must use asyncio.gather to ensure order of results is the same as the order of tasks
    # this is importance for the next step, where we group results by node
    results_sequence = await asyncio.gather(*tasks)
    # group results so that each group contains results for a single node
    num_of_evaluators = 3
    results_grouped = [
        results_sequence[i : i + num_of_evaluators]
        for i in range(0, len(results_sequence), num_of_evaluators)
    ]
    return results_grouped


async def run_complexity_evaluation_agent(
    text: str, model: str, api_key: str, complexity_definition: str
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
    # save_json(
    #     {
    #         "system_message": complexity_evaluation_agent._system_messages[0].content,
    #         "user_message": text,
    #         "response": result,
    #     },
    #     "complexity_evaluation.json",
    # )
    return 1 if result == "Yes" else 0


async def run_coherence_evaluation_agent(
    parent_part: str,
    child_part: str,
    model: str,
    api_key: str,
    coherence_definition: str,
):

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
    )

    coherence_evaluation_agent = AssistantAgent(
        name="coherence_evaluation_agent",
        model_client=model_client,
        # temperature=0.5,
        system_message=f"""You are a coherence evaluator. You will be given two parts of a sequence: a parent part and a child part.
Evaluate whether Child Part logically or thematically follows from Parent Part, consistent with the following definition of coherence:
{coherence_definition}

If they are coherent, respond with:
"Yes"

If they are not coherent, respond with:
"No"

Output must be EXACTLY one of these words, with no additional formatting, punctuation, or explanation.
""",
    )
    user_message = """
        - Parent Part: {parent_part}
        - Child Part: {child_part}
    """.format(
        parent_part=parent_part, child_part=child_part
    )

    response = await coherence_evaluation_agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )

    result = response.chat_message.content.strip()

    # save_json(
    #     {
    #         "system_message": coherence_evaluation_agent._system_messages[0].content,
    #         "user_message": user_message,
    #         "response": result,
    #     },
    #     "coherence_evaluation.json",
    # )
    return 1 if result == "Yes" else 0


async def run_importance_evaluation_agent(
    final_goal: str,
    subtask_description: str,
    model: str,
    api_key: str,
    importance_definition: str,
):

    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
    )

    importance_evaluation_agent = AssistantAgent(
        name="importance_evaluation_agent",
        model_client=model_client,
        # temperature=0.5,
        system_message=f"""You are an importance evaluator. You will be given a final task goal and a subtask description.
        Evaluate whether the subtask is important using the following definition:
        {importance_definition}

        If they are important, respond with:
        "Yes"

        Otherwise, respond with:
        "No"

        Output must be EXACTLY one of these words, with no additional formatting, punctuation, or explanation.
        """,
    )
    user_message = """
        - A final task goal: {final_goal}
        - A subtask description: {subtask_description}
    """.format(
        final_goal=final_goal, subtask_description=subtask_description
    )
    response = await importance_evaluation_agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )

    result = response.chat_message.content.strip()
    # save_json(
    #     {
    #         "system_message": importance_evaluation_agent._system_messages[0].content,
    #         "user_message": user_message,
    #         "response": result,
    #     },
    #     "importance_evaluation.json",
    # )
    return 1 if result == "Yes" else 0
