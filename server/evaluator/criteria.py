from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from tqdm import tqdm
import asyncio
import itertools
from server.custom_types import MCT_Node

import json
import re


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
Your job is to decide if the text is complex (hard) or NOT complex (easy) based on the following definition:
{complexity_definition}

If the text is complex, respond with:
"Yes"

If the text is NOT complex, respond with:
"No"

You must output your reasoning in a <REASONING>...</REASONING> block, then provide your final decision in a <RESULT>...</RESULT> block. The <RESULT> block must contain EXACTLY "Yes" or "No" (nothing else).

Example format:
<REASONING>This is my reasoning about complexity.</REASONING>
<RESULT>Yes</RESULT>
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
                    content=(
                        f"<REASONING>{example['user_reasoning']}</REASONING>\n"
                        f"<RESULT>{'Yes' if example['user_evaluation'] else 'No'}</RESULT>"
                    ),
                    source="assistant",
                )
            )

    user_message = task_def_toString(node, goal)
    messages = few_shot_messages + [TextMessage(content=user_message, source="user")]

    response = await complexity_evaluation_agent.on_messages(
        messages,
        cancellation_token=CancellationToken(),
    )

    result_text = response.chat_message.content.strip()

    reasoning_match = re.search(r"<REASONING>(.*?)</REASONING>", result_text, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

    result_match = re.search(r"<RESULT>(.*?)</RESULT>", result_text, re.DOTALL)
    final_result = result_match.group(1).strip() if result_match else "ERR"

    complexity_value = 1 if final_result == "No" else 0 if final_result == "Yes" else -1

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

    return complexity_value


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
Evaluate whether the child part logically or thematically follows from the parent part according to the following definition of coherence:
{coherence_definition}

You must output your reasoning in a <REASONING>...</REASONING> block, then provide your final decision in a <RESULT>...</RESULT> block. The <RESULT> block must contain EXACTLY "Yes" or "No" (nothing else).

Example format:
<REASONING>This is my reasoning about coherence.</REASONING>
<RESULT>Yes/No</RESULT>
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
            example_reasoning = example["user_reasoning"]
            example_eval = example["user_evaluation"]

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
                    content=(
                        f"<REASONING>{example_reasoning}</REASONING>\n"
                        f"<RESULT>{'Yes' if example_eval else 'No'}</RESULT>"
                    ),
                    source="assistant",
                )
            )

    user_message = user_message_generator(parent_node, child_node)
    messages = few_shot_messages + [TextMessage(content=user_message, source="user")]

    response = await coherence_evaluation_agent.on_messages(
        messages,
        cancellation_token=CancellationToken(),
    )

    result_text = response.chat_message.content.strip()

    reasoning_match = re.search(r"<REASONING>(.*?)</REASONING>", result_text, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

    result_match = re.search(r"<RESULT>(.*?)</RESULT>", result_text, re.DOTALL)
    final_result = result_match.group(1).strip() if result_match else "ERR"

    coherence_value = 1 if final_result == "Yes" else 0 if final_result == "No" else -1

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

    return coherence_value


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

You must output your reasoning in a <REASONING>...</REASONING> block, then provide your final decision in a <RESULT>...</RESULT> block. The <RESULT> block must contain EXACTLY "Yes" or "No" (nothing else).

Example format:
<REASONING>This is my reasoning about importance.</REASONING>
<RESULT>Yes/No</RESULT>
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
            example_reasoning = example["user_reasoning"]
            example_evaluation = example["user_evaluation"]
            few_shot_messages.append(
                TextMessage(
                    content=user_message_generator(
                        goal, MCT_Node.model_validate(example["node"])
                    ),
                    source="user",
                    source="user",
                )
            )

            few_shot_messages.append(
                TextMessage(
                    content=(
                        f"<REASONING>{example_reasoning}</REASONING>\n"
                        f"<RESULT>{'Yes' if example_evaluation else 'No'}</RESULT>"
                    ),
                    source="assistant",
                )
            )

    user_message = user_message_generator(goal, node)
    messages = few_shot_messages + [TextMessage(content=user_message, source="user")]

    response = await importance_evaluation_agent.on_messages(
        messages,
        cancellation_token=CancellationToken(),
    )

    result_text = response.chat_message.content.strip()

    reasoning_match = re.search(r"<REASONING>(.*?)</REASONING>", result_text, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

    result_match = re.search(r"<RESULT>(.*?)</RESULT>", result_text, re.DOTALL)
    final_result = result_match.group(1).strip() if result_match else "ERR"

    importance_value = 1 if final_result == "Yes" else 0 if final_result == "No" else -1

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

    return importance_value
