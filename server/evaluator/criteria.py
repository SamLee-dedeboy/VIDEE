from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from tqdm import tqdm
import asyncio
import itertools
from server.custom_types import MCT_Node


import json


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def task_def_toString(task: MCT_Node, goal: str):
    if task.MCT_id == "-1":
        return goal
    return """
    Task: {label}
    Description: {description}
    """.format(
        label=task.label, description=task.description
    )


async def run_all_evaluations(
    goal: str,
    eval_params: list[tuple[str, dict, dict]],  # [goal, node, parent_node]
    eval_definitions: dict[str, str],
    eval_few_shot_examples: dict[str, list[dict]],
    model: str,
    api_key: str,
):
    """Run all evaluation agents for all nodes. Each node is evaluated for complexity, coherence, and importance.
    Args:
        goal: The final task goal. (necessary for coherence)
        eval_params: A list of tuples, each containing the goal, node, and parent node to evaluate.
        eval_definitions: The definitions of complexity, coherence, and importance.
        eval_few_shot_examples: Few-shot examples for the evaluation. (optional)
        model: The model to use for evaluation.
        api_key: The API key for the model.
    """
    nested_tasks = []
    for goal, node, parent_node in eval_params:
        node = MCT_Node.model_validate(node)
        parent_node = MCT_Node.model_validate(parent_node)
        nested_tasks.append(
            [
                run_complexity_evaluation_agent(
                    goal=goal,
                    node=node,
                    model=model,
                    api_key=api_key,
                    complexity_definition=eval_definitions["complexity"],
                    few_shot_examples=(
                        eval_few_shot_examples["complexity"]
                        if "complexity" in eval_few_shot_examples
                        else []
                    ),
                ),
                run_coherence_evaluation_agent(
                    goal=goal,
                    parent_node=parent_node,
                    child_node=node,
                    model=model,
                    api_key=api_key,
                    coherence_definition=eval_definitions["coherence"],
                    few_shot_examples=(
                        eval_few_shot_examples["coherence"]
                        if "coherence" in eval_few_shot_examples
                        else []
                    ),
                ),
                run_importance_evaluation_agent(
                    goal=goal,
                    node=node,
                    model=model,
                    api_key=api_key,
                    importance_definition=eval_definitions["importance"],
                    few_shot_examples=(
                        eval_few_shot_examples["importance"]
                        if "importance" in eval_few_shot_examples
                        else []
                    ),
                ),
            ]
        )
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
    goal: str,
    node: MCT_Node,
    model: str,
    api_key: str,
    complexity_definition: str,
    few_shot_examples: list[dict],
):
    """
    Run the complexity evaluation agent to evaluate whether the node is complex.
    Args:
        goal: The final task goal. (not actually used in the evaluation)
        node: The node to evaluate.
        model: The model to use for evaluation.
        api_key: The API key for the model.
        complexity_definition: The definition of complexity.
        few_shot_examples: Few-shot examples for the evaluation. (optional)
    """

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
    few_shot_messages = []
    if len(few_shot_examples) > 0:
        for example in few_shot_examples:
            few_shot_messages.append(
                TextMessage(
                    content=task_def_toString(
                        MCT_Node.model_validate(example["node"]), goal
                    ),
                    source="user",
                )
            )
            few_shot_messages.append(
                TextMessage(
                    content="Yes" if example["user_evaluation"] else "No",
                    source="assistant",
                )
            )

    node_text = task_def_toString(node, goal)
    response = await complexity_evaluation_agent.on_messages(
        few_shot_messages + [TextMessage(content=node_text, source="user")],
        cancellation_token=CancellationToken(),
    )
    result = response.chat_message.content.strip()

    # save_json(
    #     {
    #         "system_message": complexity_evaluation_agent._system_messages[0].content,
    #         "few_shot_messages": list(
    #             map(lambda m: m.source + ": " + m.content, few_shot_messages)
    #         ),
    #         "response": result,
    #     },
    #     "complexity_evaluation.json",
    # )
    return 1 if result == "Yes" else 0


async def run_coherence_evaluation_agent(
    goal: str,
    parent_node: MCT_Node,
    child_node: MCT_Node,
    model: str,
    api_key: str,
    coherence_definition: str,
    few_shot_examples: list[dict],
):
    """
    Run the coherence evaluation agent to evaluate whether the child node is coherent with the parent node.
    Args:
        goal: The final task goal. (not actually used in the evaluation)
        parent_node: The parent node.
        child_node: The child node. (the node to evaluate)
        model: The model to use for evaluation.
        api_key: The API key for the model.
        coherence_definition: The definition of coherence.
        few_shot_examples: Few-shot examples for the evaluation. (optional)
    """

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
    user_message_generator = lambda _parent_node, _child_node: """
        - Parent Part: {parent_part}
        - Child Part: {child_part}
    """.format(
        parent_part=task_def_toString(_parent_node, goal),
        child_part=task_def_toString(_child_node, goal),
    )

    few_shot_messages = []
    if len(few_shot_examples) > 0:
        for example in few_shot_examples:
            few_shot_messages.append(
                TextMessage(
                    content=user_message_generator(
                        MCT_Node.model_validate(example["parent_node"]),
                        MCT_Node.model_validate(example["node"]),
                    ),
                    source="user",
                )
            )
            few_shot_messages.append(
                TextMessage(
                    content="Yes" if example["user_evaluation"] else "No",
                    source="assistant",
                )
            )

    user_message = user_message_generator(parent_node, child_node)

    response = await coherence_evaluation_agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )

    result = response.chat_message.content.strip()

    # save_json(
    #     {
    #         "system_message": coherence_evaluation_agent._system_messages[0].content,
    #         "few_shot_messages": list(
    #             map(lambda m: m.source + ": " + m.content, few_shot_messages)
    #         ),
    #         "response": result,
    #     },
    #     "coherence_evaluation.json",
    # )
    return 1 if result == "Yes" else 0


async def run_importance_evaluation_agent(
    goal: str,
    node: MCT_Node,
    model: str,
    api_key: str,
    importance_definition: str,
    few_shot_examples: list[dict],
):
    """
    Run the importance evaluation agent to evaluate whether the node is important.
    Args:
        goal: The final task goal. (necessary for the evaluation)
        node: The node to evaluate.
        model: The model to use for evaluation.
        api_key: The API key for the model.
        importance_definition: The definition of importance.
        few_shot_examples: Few-shot examples for the evaluation. (optional)
    """

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

    user_message_generator = lambda _goal, _node: """
        - A final task goal: {final_goal}
        - A subtask description: {subtask_description}
    """.format(
        final_goal=_goal, subtask_description=task_def_toString(_node, goal)
    )
    few_shot_messages = []
    if len(few_shot_examples) > 0:
        for example in few_shot_examples:
            few_shot_messages.append(
                TextMessage(
                    content=user_message_generator(
                        goal, MCT_Node.model_validate(example["node"])
                    ),
                    source="user",
                )
            )
            few_shot_messages.append(
                TextMessage(
                    content="Yes" if example["user_evaluation"] else "No",
                    source="assistant",
                )
            )

    user_message = user_message_generator(goal, node)
    response = await importance_evaluation_agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )

    result = response.chat_message.content.strip()
    # save_json(
    #     {
    #         "system_message": importance_evaluation_agent._system_messages[0].content,
    #         "few_shot_messages": list(
    #             map(lambda m: m.source + ": " + m.content, few_shot_messages)
    #         ),
    #         "response": result,
    #     },
    #     "importance_evaluation.json",
    # )
    return 1 if result == "Yes" else 0
