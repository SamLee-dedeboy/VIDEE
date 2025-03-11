from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
import asyncio
import itertools
from server.custom_types import MCT_Node, ScoreWithReasoning
from .agents import get_agents, get_response, get_openai_client

import json
import re
import yaml
import os

dirname = os.path.dirname(__file__)
relative_path = lambda filename: os.path.join(dirname, filename)


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def task_def_toString(task: MCT_Node, goal: str):
    if task.MCT_id == "-1":
        return goal
    return "\nTask: {label}\nDescription: {description}\n".format(
        label=task.label, description=task.description
    )


def load_system_message(criteria):
    with open(
        relative_path("eval_definitions/system_messages.yaml"), "r", encoding="utf-8"
    ) as f:
        system_messages = yaml.safe_load(f)
    return system_messages.get(criteria, "")


def parse_result(result_text: str, flip: bool = False) -> ScoreWithReasoning:
    reasoning_match = re.search(r"<REASONING>(.*?)</REASONING>", result_text, re.DOTALL)
    if not reasoning_match:
        raise ValueError("Missing <REASONING> section in result text.")

    result_match = re.search(r"<RESULT>(.*?)</RESULT>", result_text, re.DOTALL)
    if not result_match:
        raise ValueError("Missing <RESULT> section in result text.")

    reasoning = reasoning_match.group(1).strip()
    final_result = result_match.group(1).strip()

    if final_result == "Yes":
        value = 1
    elif final_result == "No":
        value = 0
    else:
        raise ValueError(
            f"Unexpected <RESULT> value: '{final_result}'. Expected 'Yes' or 'No'."
        )

    if flip:
        value = 1 - value
    return ScoreWithReasoning(value=value, reasoning=reasoning)
    return {"value": value, "reason": reasoning}


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
) -> ScoreWithReasoning:
    """
    Run the complexity evaluation agent to evaluate whether the node is complex.
    Args:
        goal: The final task goal. (not actually used in the evaluation)
        node: The node to evaluate.
        model: The model to use for evaluation.
        api_key: The API key for the model.
        complexity_definition: The definition of complexity.
        few_shot_examples: Few-shot examples for the evaluation. (optional)
    Returns:
        A dictionary containing the evaluation results for the node.
        Key: The model name.
        Value: The evaluation result.
    """

    system_message = load_system_message("complexity_evaluator").format(
        definition=complexity_definition
    )
    agents = get_agents(
        agent_name="complexity_evaluator", system_message=system_message
    )

    few_shot_messages = []
    for example in few_shot_examples:
        user_reasoning = example.get("user_reasoning", "").strip()
        if not user_reasoning:
            user_reasoning = await get_llm_reasoning(
                criteria="complexity",
                content=task_def_toString(
                    MCT_Node.model_validate(example["node"]), goal
                ),
                answer=example["user_evaluation"],
                definition=complexity_definition,
            )

        few_shot_messages.extend(
            [
                TextMessage(
                    content=task_def_toString(
                        MCT_Node.model_validate(example["node"]), goal
                    ),
                    source="user",
                ),
                TextMessage(
                    content=f"<REASONING>{user_reasoning}</REASONING>\n"
                    f"<RESULT>{'Yes' if example['user_evaluation'] else 'No'}</RESULT>",
                    source="assistant",
                ),
            ]
        )

    user_message = task_def_toString(node, goal)
    messages = few_shot_messages + [TextMessage(content=user_message, source="user")]

    results = await asyncio.gather(
        *[get_response(agent, messages) for _, agent in agents]
    )

    parsed_results = {
        model: parse_result(result_text, flip=True)
        for (model, _), result_text in zip(agents, results)
    }

    # TODO: Aggregate results from multiple models
    return parsed_results[agents[0][0]].value


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

    system_message = load_system_message("coherence_evaluator").format(
        definition=coherence_definition
    )
    agents = get_agents(agent_name="coherence_evaluator", system_message=system_message)

    def user_message_generator(_parent_node, _child_node):
        return """
        - Parent Part: {parent_part}
        - Child Part: {child_part}
        """.format(
            parent_part=task_def_toString(_parent_node, goal),
            child_part=task_def_toString(_child_node, goal),
        )

    few_shot_messages = []
    for example in few_shot_examples:
        user_reasoning = example.get("user_reasoning", "").strip()

        if not user_reasoning:
            user_reasoning = await get_llm_reasoning(
                criteria="coherence",
                content=user_message_generator(
                    MCT_Node.model_validate(example["parent_node"]),
                    MCT_Node.model_validate(example["node"]),
                ),
                answer=example["user_evaluation"],
                definition=coherence_definition,
            )

        few_shot_messages.extend(
            [
                TextMessage(
                    content=user_message_generator(
                        MCT_Node.model_validate(example["parent_node"]),
                        MCT_Node.model_validate(example["node"]),
                    ),
                    source="user",
                ),
                TextMessage(
                    content=f"<REASONING>{user_reasoning}</REASONING>\n"
                    f"<RESULT>{'Yes' if example['user_evaluation'] else 'No'}</RESULT>",
                    source="assistant",
                ),
            ]
        )

    user_message = user_message_generator(parent_node, child_node)
    messages = few_shot_messages + [TextMessage(content=user_message, source="user")]

    results = await asyncio.gather(
        *[get_response(agent, messages) for _, agent in agents]
    )

    parsed_results = {
        model: parse_result(result_text, flip=False)
        for (model, _), result_text in zip(agents, results)
    }

    # TODO: Aggregate results from multiple models
    return parsed_results[agents[0][0]].value


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

    system_message = load_system_message("importance_evaluator").format(
        definition=importance_definition
    )

    agents = get_agents(
        agent_name="importance_evaluator", system_message=system_message
    )

    def user_message_generator(_goal, _node):
        return """
        - A final task goal: {final_goal}
        - A subtask description: {subtask_description}
        """.format(
            final_goal=_goal, subtask_description=task_def_toString(_node, goal)
        )

    few_shot_messages = []
    for example in few_shot_examples:
        user_reasoning = example.get("user_reasoning", "").strip()

        if not user_reasoning:
            user_reasoning = await get_llm_reasoning(
                criteria="importance",
                content=user_message_generator(
                    goal, MCT_Node.model_validate(example["node"])
                ),
                answer=example["user_evaluation"],
                definition=importance_definition,
            )

        few_shot_messages.extend(
            [
                TextMessage(
                    content=user_message_generator(
                        goal, MCT_Node.model_validate(example["node"])
                    ),
                    source="user",
                ),
                TextMessage(
                    content=f"<REASONING>{user_reasoning}</REASONING>\n"
                    f"<RESULT>{'Yes' if example['user_evaluation'] else 'No'}</RESULT>",
                    source="assistant",
                ),
            ]
        )

    user_message = user_message_generator(goal, node)
    messages = few_shot_messages + [TextMessage(content=user_message, source="user")]

    results = await asyncio.gather(
        *[get_response(agent, messages) for _, agent in agents]
    )

    parsed_results = {
        model: parse_result(result_text, flip=False)
        for (model, _), result_text in zip(agents, results)
    }

    # return parsed_results
    # TODO: Aggregate results from multiple models
    return parsed_results[agents[0][0]].value


async def get_llm_reasoning(
    criteria: str, content: str, answer: bool, definition: str = ""
) -> str:
    system_message = load_system_message(f"{criteria}_reasoner").format(
        definition=definition
    )
    with open(relative_path("model_list.yaml"), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        model_name = data.get("reason-model", "o1")

    model_client = get_openai_client(model_name)
    if model_client is None:
        raise RuntimeError(
            "Missing OpenAI API key. Please set 'OPENAI_API_KEY' in the dot environment file '.env'."
        )

    answer_map = {
        "complexity": {True: "simple", False: "complex"},
        "coherence": {True: "coherent", False: "incoherent"},
        "importance": {True: "important", False: "unimportant"},
    }
    answer_text = answer_map.get(criteria, {True: "Yes", False: "No"}).get(
        answer, "Unknown"
    )

    prompt = f"""Given content: {content}

The user's final decision is {answer_text}

Provide a reasoning explanation:
"""

    reasoning_agent = AssistantAgent(
        name="llm_reasoning_agent",
        model_client=model_client,
        system_message=system_message,
    )

    response = await get_response(
        reasoning_agent, [TextMessage(content=prompt, source="user")]
    )

    return response
