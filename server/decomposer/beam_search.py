import server.AutoGenUtils.query as autogen_utils
import random
import copy
from collections import defaultdict


async def goal_decode_n_samples(
    goal: str, previous_steps: list, model: str, api_key: str, n: int = 2
):
    candidate_steps = []
    next_steps = await autogen_utils.run_goal_decomposition_agent_stepped(
        goal, previous_steps, model, api_key, n
    )
    evaluation_scores = await autogen_utils.run_decomposition_self_evaluation_agent(
        goal, previous_steps, next_steps, model, api_key, n
    )
    for next_step, evaluation_score in zip(next_steps, evaluation_scores):
        new_beam = copy.deepcopy(previous_steps)
        new_beam.append(next_step)
        candidate_steps.append((new_beam, evaluation_score))

    # add parents and children
    for i, (decomposed_semantic_tasks, eval_score) in enumerate(candidate_steps):
        for j, task in enumerate(decomposed_semantic_tasks):
            task["confidence"] = random.random()
            task["complexity"] = random.random()
            decomposed_semantic_tasks[j] = task
        decomposed_semantic_tasks = add_children(decomposed_semantic_tasks)
    candidate_steps[i] = (decomposed_semantic_tasks, eval_score)
    return candidate_steps


async def beam_search_decomposition_step(
    goal: str, candidate_steps: list, model: str, api_key: str, k: int = 2, n: int = 2
):
    new_candidates = []
    for beam, score in candidate_steps:
        previous_steps = beam
        if previous_steps[-1]["label"] == "END":
            continue
        new_candidates += await goal_decode_n_samples(
            goal, previous_steps, model, api_key, n
        )
    candidate_steps = new_candidates
    # sort by score
    candidate_steps.sort(key=lambda x: x[1], reverse=True)
    # select top k steps
    candidate_steps = candidate_steps[:k]

    # add parents and children
    for i, (decomposed_semantic_tasks, eval_score) in enumerate(candidate_steps):
        for j, task in enumerate(decomposed_semantic_tasks):
            task["confidence"] = random.random()
            task["complexity"] = random.random()
            decomposed_semantic_tasks[j] = task
        # decomposed_semantic_tasks = prune_redundant_parents(decomposed_semantic_tasks)
        decomposed_semantic_tasks = add_children(decomposed_semantic_tasks)
    candidate_steps[i] = (decomposed_semantic_tasks, eval_score)
    return candidate_steps


async def stream_goal_beam_search(
    goal: str, candidate_steps: list, model: str, api_key: str, k: int = 2, n: int = 2
):
    while True:
        candidate_steps = await beam_search_decomposition_step(
            goal, candidate_steps, model, api_key, k=k, n=n
        )
        yield candidate_steps
        if len(candidate_steps) > 0 and all(
            [beam[-1]["label"] == "END" for beam, _ in candidate_steps]
        ):
            break
        # break
        # time.sleep(5)  # Simulating processing time


def add_children(decomposed_steps):
    children_dict = defaultdict(list)
    for i, step in enumerate(decomposed_steps):
        step["id"] = str(step["id"])
        step["children"] = []
        step["sub_tasks"] = []
        step["parentIds"] = list(map(lambda x: str(x), step["parentIds"]))
        for parent in step["parentIds"]:
            children_dict[parent].append(step["id"])
        decomposed_steps[i] = step
    for i, step in enumerate(decomposed_steps):
        step["children"] = children_dict[step["id"]]
        decomposed_steps[i] = step
    return decomposed_steps
