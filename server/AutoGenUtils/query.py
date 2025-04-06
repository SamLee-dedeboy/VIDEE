import json
from server.custom_types import Node, PrimitiveTaskDescription
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from tqdm import tqdm
import asyncio
import re

from server.utils import extract_json_content, retry_llm_json_extraction


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True, ensure_ascii=False)


async def call_agent(agent, user_message):
    response = await agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )
    return response


async def parallel_call_agents_repeat(n, agent, user_message):
    """Repeatedly call the agent n times."""
    tasks = [call_agent(agent, user_message) for _ in range(n)]

    results = await asyncio.gather(*tasks)
    return results


async def parallel_call_agents(agent, user_messages):
    """Call the agent for each user message in parallel."""
    tasks = [call_agent(agent, user_message) for user_message in user_messages]

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

    # Use retry_llm_json_extraction instead of extract_json_content
    result = await retry_llm_json_extraction(
        llm_call_func=goal_decomposition_agent.on_messages,
        llm_call_args=([TextMessage(content=goal, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        expected_key="steps",
        max_retries=3,
    )

    # If we couldn't get a valid result after all retries, return an empty list
    if result is None:
        return []

    return result


async def run_goal_decomposition_agent_stepped(
    goal: str,
    previous_steps: list,
    model: str,
    api_key: str,
    temperature=0.0,
    n=1,
    remain_steps=5,
):
    if remain_steps <= 0:
        ids = list(map(lambda step: step["id"], previous_steps))
        return [
            {
                # "id": "END_PATH_" + str(ids),
                "label": "END",
                "description": "END",
                "explanation": "END",
                "parentIds": ids,
            }
            for _ in range(n)
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
        Your task is to provide a single next step, but with {n} possible alternatives for user to choose.
        Focus on the conceptual next step in terms of text analytics. If no further steps are needed, label the next step with "END".
        There plan should not be more than 5 steps.
        ** Requirements **
        The name of the step should be one concise noun-phrase.
        The abstraction level of the step should be appropriate for high-level planning and communication with non-technical people.
        For the parentIds, provide the ids of the steps that this step **directly** depends on in terms of input-output data.
        The alternatives should have varying complexity, coherence with previous steps, and importance.
        The whole pipeline should emphasize concise and clear steps, with as few steps as possible and no more than 5 steps.
        DO NOT output steps like data collection, implementation, validation or any steps related to communication such as visualization or reporting.
        Reply with this JSON format. Do not wrap the json codes in JSON markers. Do not include any comments.
            {{
                "next_steps": [
                    {{
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
    user_message += "There are maximally {remaining_steps} steps remaining until you have to finish the task.\n".format(
        remaining_steps=remain_steps
    )

    # Use the new retry_llm_json_extraction function to handle both the LLM call and JSON extraction
    result = await retry_llm_json_extraction(
        llm_call_func=goal_decomposition_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        expected_key="next_steps",
        max_retries=5,
        retry_delay=1.0,
        backoff_factor=2.0,
    )

    # If we couldn't get a valid result after all retries, return a default "END" step
    if result is None:
        ids = list(map(lambda step: step["id"], previous_steps))
        return [
            {
                # "id": "END_PATH_" + str(ids) + "_FALLBACK",
                "label": "END",
                "description": "Unable to determine next steps after multiple attempts",
                "explanation": "The system encountered difficulties determining the next steps",
                "parentIds": ids,
            }
            for _ in range(n)
        ]

    return result


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
        # Use the retry_llm_json_extraction function
        result = await retry_llm_json_extraction(
            llm_call_func=decomposition_self_evaluation_agent.on_messages,
            llm_call_args=([TextMessage(content=user_message, source="user")],),
            llm_call_kwargs={"cancellation_token": CancellationToken()},
            expected_key="evaluation_score",
            max_retries=3,
            retry_delay=1.0,
            backoff_factor=2.0,
        )

        # If we couldn't get a valid result after all retries, return a default score
        if result is None:
            return 3  # Return a neutral score as fallback

        return result
    else:
        responses = await parallel_call_agents_repeat(
            n, decomposition_self_evaluation_agent, user_message
        )
        responses = [
            extract_json_content(response.chat_message.content)["evaluation_score"]
            for response in responses
        ]
        return responses


async def run_stepped_decomposition_to_primitive_task_agent(
    tree: list[Node],
    primitive_task_list: list[PrimitiveTaskDescription],
    model: str,
    api_key: str,
) -> None:
    # Prepare primitive task definitions string once for reuse
    primitive_task_defs_str = ""
    for primitive_task in primitive_task_list:
        primitive_task_defs_str += "<primitive_task>\n"
        for key, value in primitive_task.items():
            primitive_task_defs_str += f"<{key}>{value}</{key}>\n"
        primitive_task_defs_str += "</primitive_task>\n"

    # Create a comma-separated string of valid primitive task labels
    supported_labels_str = primitive_task_list[0]["label"]
    for primitive_task in primitive_task_list[1:]:
        supported_labels_str += f",{primitive_task['label']}"

    # Generate primitve task Label to attribute mappings
    label_to_attribute_mapping = {}
    for primitive_task in primitive_task_list:
        label_to_attribute_mapping[primitive_task['label']] = primitive_task

    # Configure the model client
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

    # Create the agent with the system message
    decomposition_to_primitive_task_agent = AssistantAgent(
        name="decomposition_to_primitive_task_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are a Natural Language Processing (NLP) assistant. You are given a list of primitive NLP tasks that could be used.
        Here is the list of primitive NLP tasks:
        {primitive_task_defs}

        ** Task **
        The user will describe a series of real-world tasks (semantic tasks). Your job is to convert each **currently focused** semantic task into one or more primitive NLP tasks necessary to accomplish **its specific goal**. You will process one semantic task at a time, considering previously generated primitive tasks AND the description of the **next** semantic task to avoid overlap.

        ** Requirements **
        The ids of each formulated NLP task must be unique, even if the labels are the same. This will help users correctly identify the dependent steps.
        If the same label appears multiple times, use the ids to differentiate them.
        For example, use 'Information Extraction-1' and 'Information Extraction-2' as ids.

        1. CRITICAL: The "label" field in your output MUST ONLY use one of these exact labels from the primitive task list, i.e.: {supported_labels}
        DO NOT create custom labels like "Graph Construction" or "Information Extraction" that aren't in the list above.

        2. CRITICAL: A single semantic task often requires MULTIPLE primitive tasks chained together. Don't try to force-fit a semantic task into a single primitive task.

        3. CRITICAL: STRICTLY enforce input/output compatibility between primitive tasks:
           - Pay close attention to the `input` and `output` types specified for each primitive task in the provided definitions ({primitive_task_defs}).
           - The `output` type of *every* prerequisite task listed in the `depend_on` field MUST SEMANTICALLY MATCH the required `input` type of the current primitive task.
           - For example, "Clustering Analysis" requires `Vector Representation` input. Therefore, its `depend_on` field MUST ONLY contain IDs of tasks whose `output` is `Vector Representation` (like "Embedding Generation" or "Dimensionality Reduction"). Depending on a task outputting `List[Category Label (Text)]` (like "Document Classification") is strictly forbidden for "Clustering Analysis". See Example 6.

        4. CRITICAL: Correctly handle dependencies WITHIN the current step. If you generate multiple primitive tasks (e.g., Task A followed by Task B) to solve the *single current semantic task*, ensure Task B correctly lists the ID of Task A in its `depend_on` field if Task B requires the output of Task A. DO NOT mistakenly depend on tasks generated for previous semantic tasks if a suitable prerequisite (Task A) is being generated in the current step.

        5. For tasks that depend on other primitive tasks (either generated in this step or previous steps), specify the dependency using the "depend_on" field, referencing the `id` of the prerequisite task(s).
           CRITICAL: If a primitive task is the very first one being generated in the entire workflow (i.e., no previous primitive tasks exist from prior semantic tasks AND it's the first primitive task for the current semantic task), its `depend_on` field MUST be an empty list `[]`. Do not hallucinate dependencies.

        6. CRITICAL: MAXIMIZE REUSE of existing primitive tasks from PREVIOUS steps. Before proposing ANY new primitive task, you MUST check the list of `<primitive_task>` provided in the user message (`Here are the primitive tasks I've already created...`). If an existing task serves the *exact* same purpose (e.g., generating embeddings from the same source data for a subsequent similar semantic task), you MUST reference its `id` in the `depend_on` field of the subsequent task instead of creating a duplicate. Only create a new primitive task if it operates on genuinely different input data or requires significantly different processing logic or parameters. Explain in the 'explanation' field why a new task is needed if it seems similar to an existing one. See Example 5.

        7. CRITICAL: STRICTLY ADHERE to `allow_multiple_parents` constraint.
            - If `allow_multiple_parents` is `true` for a primitive task type, a generated task of that type *can* have multiple `depend_on` entries, referencing IDs of previously generated primitive tasks.
            - If `allow_multiple_parents` is `false` for a primitive task type, a generated task of that type MUST have *at most one* entry in its `depend_on` field.
            - **MANDATORY INTERMEDIATE STEP:** If a task with `allow_multiple_parents: false` logically requires input resulting from multiple distinct preceding primitive tasks (e.g., depends on outputs from `TaskA` and `TaskB`), you MUST NOT list both `TaskA` and `TaskB` in its `depend_on`. Instead, you MUST first introduce an intermediate primitive task (choose either "Data Transformation" or "Insights Summarization" based on what makes more sense - usually "Data Transformation" for combining data structures). This intermediate task's `depend_on` should list `TaskA` and `TaskB` (assuming the intermediate task type allows multiple parents). Then, the original task (the one with `allow_multiple_parents: false`) MUST depend *only* on the ID of this newly introduced intermediate task. See Example 4 for the correct structure.

        8. CRITICAL: DO NOT GENERATE PRIMITIVE TASKS FOR FUTURE SEMANTIC TASKS. Look at the `<next_semantic_task>` provided in the user message. If a potential primitive task's primary purpose seems to directly address the goal of the *next* semantic task rather than the *current* one, you MUST NOT generate it now. Defer its generation until that next semantic task is processed. Focus only on the primitive steps strictly necessary for the *currently focused* semantic task. See Example 7.

        9. CRITICAL: SPECIAL RULE FOR CLUSTERING ANALYSIS: The primitive task "Clustering Analysis" requires `Vector Representation` as input. Therefore, any generated "Clustering Analysis" task MUST have a `depend_on` field containing ONLY the ID(s) of prerequisite task(s) that output `Vector Representation`. Currently, only "Embedding Generation" and "Dimensionality Reduction" produce this output type. Depending on ANY other task type (like "Insights Summarization", "Label Generation", "Document Classification", "Data Transformation", etc.) for "Clustering Analysis" is ABSOLUTELY FORBIDDEN. Check this rule meticulously for every "Clustering Analysis" task you generate.

        ** Examples of Common Task Chains **

        Example 1 - Document clustering:
        - Semantic task: "Cluster documents by topic"
        - Primitive tasks needed (generated together for this semantic task):
          1. `Embedding Generation-1` (label: "Embedding Generation", input: Text, output: `Vector Representation`, `allow_multiple_parents: false`, `depend_on: []` if first task overall, otherwise depends on prior text processing)
          2. `Clustering Analysis-1` (label: "Clustering Analysis", input: `Vector Representation`, output: `List[Cluster Label]`, `allow_multiple_parents: false`, `depend_on: ["Embedding Generation-1"]`) <- Correctly depends on the task generated *within* this step. Strictly follows Rule 9.

        Example 2 - Entity-based analysis:
        - Semantic task: "Find relationships between companies mentioned in text"
        - Primitive tasks needed (generated together for this semantic task):
          1. `Entity Extraction-1` (label: "Entity Extraction", `allow_multiple_parents: true`)
          2. `Relationship Extraction-1` (label: "Relationship Extraction", `allow_multiple_parents: true`, `depend_on: ["Entity Extraction-1"]`)

        Example 3 - Analyze document similarities:
        - Semantic task: "Analyze similarities on the given documents"
        - Primitive tasks needed (generated together for this semantic task):
          1. `Embedding Generation-2` (label: "Embedding Generation", `allow_multiple_parents: false`)
          2. `Clustering Analysis-2` (label: "Clustering Analysis", `allow_multiple_parents: false`, `depend_on: ["Embedding Generation-2"]`) <- Depends on the embedding generated in this step. Strictly follows Rule 9.

        Example 4 - Handling `allow_multiple_parents: false` with multiple inputs:
        - Semantic task: "Generate embeddings based on both document summaries and extracted entities"
        - Primitive tasks needed (generated together for this semantic task):
          1. `Summarization-1` (label: "Summarization", `allow_multiple_parents: true`)
          2. `Entity Extraction-2` (label: "Entity Extraction", `allow_multiple_parents: true`)
          3. `Data Transformation-1` (label: "Data Transformation", `allow_multiple_parents: true`, `depend_on: ["Summarization-1", "Entity Extraction-2"]`)
          4. `Embedding Generation-3` (label: "Embedding Generation", `allow_multiple_parents: false`, `depend_on: ["Data Transformation-1"]`) <- Depends *only* on the intermediate task.
        - WRONG: `Embedding Generation-3` having `depend_on: ["Summarization-1", "Entity Extraction-2"]`.

        Example 5 - Reusing tasks from previous steps:
        - Context: Assume previous semantic tasks already generated `Embedding Generation-1`.
            - Current Semantic task: "Summarize document relationships based on topics"
            - Primitive tasks needed:
                1. `Dimensionality Reduction-2` (label: "Dimensionality Reduction", `allow_multiple_parents: false`, `depend_on: ["Embedding Generation-1"]`) <- REUSES the existing embeddings from a previous step.
        - Context: Assume previous semantic tasks generated `Entity Extraction-1`.
            - Current Semantic task: "Summarize findings about extracted entities"
            - Primitive tasks needed:
                1. `Insights Summarization-1` (label: "Insights Summarization", `allow_multiple_parents: true`, `depend_on: ["Entity Extraction-1"]`) <- REUSES the existing entities.

        Example 6 - Input/Output Mismatch Violation:
        - Context: Assume previous semantic task generated `Document Classification-1` (output: `List[Category Label (Text)]`).
        - Current Semantic task: "Group documents based on content similarity"
        - Primitive tasks needed:
          1. `Embedding Generation-4` (label: "Embedding Generation", output: `Vector Representation`)
          2. `Clustering Analysis-3` (label: "Clustering Analysis", input: `Vector Representation`)
        - **WRONG** `depend_on` for `Clustering Analysis-3`: `depend_on: ["Document Classification-1"]`. This is **INVALID** because the input (`Vector Representation`) does not match the output of the dependency (`List[Category Label (Text)]`) AND violates Rule 9.
        - **CORRECT** `depend_on` for `Clustering Analysis-3`: `depend_on: ["Embedding Generation-4"]` (assuming it was generated in this step).

        Example 7 - Deferring tasks to the next semantic step:
        - Current Semantic Task: "Identify key topics in text"
        - Next Semantic Task: "Group documents by topics"
        - Primitive tasks for "Identify key topics in text":
          1. `Label Generation-1` (To extract keywords/potential topics)
          2. `Insights Summarization-2` (To synthesize findings related to topics)
        - **DEFERRED TASKS**: DO NOT generate `Embedding Generation` or `Clustering Analysis` here, even though clustering *could* reveal topics. These steps are the core of the *next* task, "Group documents by topics".
        - Later, when processing "Group documents by topics":
          1. `Embedding Generation-5` (Depends on initial text or output of "Identify key topics in text")
          2. `Clustering Analysis-4` (Depends on `Embedding Generation-5`)

        Reply with the following JSON format:
        {{ "primitive_tasks": [
                {{
                    "solves": (string) id of the user-provided semantic task that this primitive task helps solve
                    "label": (string) (MUST be one of {supported_labels})
                    "id": (str) (a unique id for the task, e.g., 'Label-1', 'Label-2'),
                    "description": (string, describe implementation procedure specific to this task)
                    "explanation": (string, explain why this primitive task is needed for the semantic task and how it differs from any similar existing tasks if applicable)
                    "depend_on": (str[], ids of the *immediately* preceding primitive task(s) that this step depends on, ensuring output type of dependency matches input type of this task. MUST be `[]` if this is the very first task.)
                }},
                ...
            ],
            "validation_check": "I confirm all labels used above are strictly from the provided primitive task list: {supported_labels}, I have maximized reuse of existing primitive tasks (Requirement 6), and I have deferred tasks belonging to the next semantic task (Requirement 8).",
            "dependency_validation_check": "I confirm strict adherence to input/output type compatibility (Requirement 3), especially the specific dependency rule for Clustering Analysis (Requirement 9). I confirm that dependencies correctly reference prerequisite tasks generated either in previous steps or within this current step (Requirement 4). I confirm that the very first task has an empty dependency list (Requirement 5). I confirm that for every primitive task generated with 'allow_multiple_parents' set to 'false', its 'depend_on' list contains at most one ID, and that intermediate tasks were correctly inserted where necessary (Requirement 7)."
        }}
        """.format(
            primitive_task_defs=primitive_task_defs_str,
            supported_labels=supported_labels_str,
        ),
    )

    # Process each semantic task one at a time
    all_primitive_tasks = []
    # Sort the tree to ensure consistent ordering (especially for dependencies)
    sorted_tree = sorted(tree, key=lambda x: x.id)
    # converted task id to label mapping
    task_id_to_label = {}

    # Create a formatted string function for a single task
    task_to_string = lambda _task: f"""
    <semantic_task>
        <id>{_task.id}</id>
        <label>{_task.label}</label>
        <description>{_task.description}</description>
        <depend_on>{_task.parentIds}</depend_on>
    </semantic_task>
    """

    manual_tasks_index = len(sorted_tree)
    # Iterate through each semantic task
    for i, semantic_task in enumerate(sorted_tree):
        if i == 0:
            continue
        # Create the user message for this specific semantic task
        user_message = f"""
        I need to implement this semantic task:
        {task_to_string(semantic_task)}
        
        Please decompose this semantic task into the necessary primitive NLP tasks that together would accomplish this goal.
        If this task depends on outputs from other primitive tasks, make sure to specify the dependencies correctly.
        Please consider the previous and next semantic tasks when decomposing the current task. DO NOT create duplicate primitive tasks that potentially belongs to the previous or next semantic tasks.

        The previous semantic task is:
        {task_to_string(sorted_tree[i - 1]) if i != 1 else "None"}
        The next semantic task is:
        {task_to_string(sorted_tree[i + 1]) if i != len(sorted_tree) - 1 else "None"}
        """

        # If there are already processed tasks, mention them for context
        if all_primitive_tasks:
            # Get the primitive tasks we've already created
            previous_tasks_str = ""
            for pt in all_primitive_tasks:
                previous_tasks_str += f"""
                <primitive_task>
                    <id>{pt['id']}</id>
                    <label>{pt['label']}</label>
                    <solves>{pt['solves']}</solves>
                </primitive_task>
                """

            user_message += f"""
            Here are the primitive tasks I've already created for other semantic tasks:
            {previous_tasks_str}
            
            You can reference these existing primitive tasks in the 'depend_on' field if appropriate.
            """

        # Get the primitive tasks for this semantic task
        result = await retry_llm_json_extraction(
            llm_call_func=decomposition_to_primitive_task_agent.on_messages,
            llm_call_args=([TextMessage(content=user_message, source="user")],),
            llm_call_kwargs={"cancellation_token": CancellationToken()},
            expected_key="primitive_tasks",
            max_retries=3,
            retry_delay=1.0,
            backoff_factor=2.0,
        )

        # If we got valid results, add them to our collection
        if result:
            # Manually add tasks to fix known issues.
            manual_tasks_to_add = []
            # update the task id to label mapping
            for task in result:
                task_id_to_label[task['id']] = task['label']
            for task_index, task in enumerate(result):
                primitive_def = label_to_attribute_mapping.get(task['label'])
                if primitive_def:
                    manual_added_task = {}
                    # If a task should not depend on multiple parents, add an intermediate task to combine the inputs.
                    # let's not do this for now, since the user can always select the unit and input key based on their needs.
                    # if primitive_def.get('allow_multiple_parents') == 'false' and len(task.get('depend_on', [])) > 1:
                    #     # Create a new "Data Transformation" primitive task
                    #     manual_added_task['id'] = f'Data Transformation-{manual_tasks_index}'
                    #     manual_added_task['description'] = f"Combine outputs from {', '.join(task['depend_on'])} for input into {task['id']}."
                    #     manual_added_task['explanation'] = f"Intermediate step to consolidate multiple inputs ({', '.join(task['depend_on'])}) required by {task['label']} ({task['id']}), which does not allow multiple parents."
                    #     manual_added_task['label'] = 'Data Transformation' # Or potentially Insights Summarization
                    #     manual_added_task['depend_on'] = task['depend_on']
                    #     manual_added_task['solves'] = task['solves'] # Associate with the same semantic task

                    # Automatically add an Embedding Generation task if tasks that require vector representations are selected but the dependency is not Embedding Generation or Dimensionality Reduction.
                    if task.get('label') in ['Clustering Analysis', 'Dimensionality Reduction'] and not any(task_id_to_label[dep] in ['Embedding Generation', 'Dimensionality Reduction'] for dep in task.get('depend_on', [])):
                        manual_added_task['id'] = f'Embedding Generation-{manual_tasks_index}'
                        manual_added_task['description'] = f"Generate embeddings to produce vector representations for the previous output data."
                        manual_added_task['explanation'] = f"Embedding Generation is a prerequisite for Further Analysis."
                        manual_added_task['label'] = 'Embedding Generation'
                        manual_added_task['depend_on'] = task['depend_on']
                        manual_added_task['solves'] = task['solves']

                    # Other potential manual fixes:
                    # - If a task has duplicated IDs, change the ID to be unique.

                    # Update the original task to depend on the new intermediate task
                    if manual_added_task:
                        task_id_to_label[manual_added_task['id']] = manual_added_task['label']
                        task['depend_on'] = [manual_added_task['id']]
                        manual_tasks_to_add.append(manual_added_task)
                        manual_tasks_index += 1

            # Add any newly created intermediate tasks to the result list
            result.extend(manual_tasks_to_add)
            # Add these primitive tasks to our overall collection
            all_primitive_tasks.extend(result)

    # Return all primitive tasks from all semantic tasks
    return all_primitive_tasks

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
    supported_labels_str = primitive_task_list[0]["label"]
    for primitive_task in primitive_task_list[1:]:
        supported_labels_str += f",{primitive_task['label']}"
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

        CRITICAL: The "label" field in your output MUST ONLY use one of these exact labels from the primitive task list, i.e.: {supported_labels}
        DO NOT create custom labels like "Graph Construction" or "Information Extraction" that aren't in the list above.  

        Reply with the following JSON format: 
        {{ "primitive_tasks": [ 
                {{ 
                    "solves": (string) id of the user-provided task that this primitive task solves
                    "label": (string) (MUST be one of {supported_labels})
                    "id": (str) (a unique id for the task),
                    "description": (string, describe implementation procedure)
                    "explanation": (string, explain why this task is needed)
                    "depend_on": (str[], ids of the task that this step depends on)
                }}, 
                {{ 
                    "solves": (string) id of the user-provided task that this primitive task solves
                    "label": (string) (MUST be one of {supported_labels})
                    "id": (str) (a unique id for the task),
                    "description": (string, describe implementation procedure)
                    "explanation": (string, explain why this task is needed)
                    "depend_on": (str[], ids of the task that this step depends on)
                }}, 
                ... 
            ],
            "validation_check": "I confirm all labels used above are strictly from the provided primitive task list: {supported_labels}"
        }}
        """.format(
            primitive_task_defs=primitive_task_defs_str,
            supported_labels=supported_labels_str,
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
    # response = await decomposition_to_primitive_task_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    #
    # return extract_json_content(response.chat_message.content)["primitive_tasks"]

    return await retry_llm_json_extraction(
        llm_call_func=decomposition_to_primitive_task_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        expected_key="primitive_tasks",
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


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
    # response = await goal_decomposition_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    # return extract_json_content(response.chat_message.content)["steps"]

    return await retry_llm_json_extraction(
        llm_call_func=goal_decomposition_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        expected_key="steps",
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


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
    # response = await decomposition_to_primitive_task_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    # return extract_json_content(response.chat_message.content)["primitive_tasks"]

    return await retry_llm_json_extraction(
        llm_call_func=decomposition_to_primitive_task_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        expected_key="primitive_tasks",
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


async def run_prompt_generation_agent(
    task: Node,
    input_keys: list,
    state_input_key: str,
    all_states_and_keys: dict,
    model: str,
    api_key: str,
):
    # Convert existing_keys to keys_by_state format
    keys_by_state = {state_input_key: input_keys}
    input_keys_str = get_existing_keys_by_state(keys_by_state)
    all_keys_str = get_all_keys_in_states(all_states_and_keys)

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
        Here are the data already exist on each document, with type and schema: {existing_keys}
        Then, generate a prompt that instructs an LLM to analyze the text using the data in each document for the user's task.
        The prompt should be a JSON object with these three sections:
        1. Context: Give instructions on what the user is trying to do.
        2. Task: Give instructions on how to analyze the text.
        3. Requirements: Provide any specific requirements or constraints for the prompt.
        4. JSON_format: A JSON object with one key, the key name should be suitable to store the result of the prompt, and value should be a valid JSON format for representing the output.
        Note: The key name of JSON_format should be DIFFERENT from any following keys: [ {all_keys_str} ]
        An example of the JSON_format section is: "{{\"themes\": [{{\"theme\": \"str\", \"definition\": \"str\"}}]}}"
        
        CRITICAL: When you generate the key name for JSON_format object, double check it is NOT EQUALS to any keys in this list: [ {all_keys_str} ]
        For example, if the existing keys are "cluster_labels,quotes,summary", the key of JSON_format SHOULD NOT be "cluster_labels" nor "quotes" nor "summary".

        Next, generate a "output_schema" key. The "output_schema" key should provide a detailed description of the output structure defined for the key in JSON_format, using the clearer schema notation (like "list[str]" or "{{'field': 'type'}}").
        for example, if the JSON_format is defined as "{{\"themes\": [{{\"theme\": \"str\", \"definition\": \"str\"}}]}}"
        the output_schema should be: "output_schema": "{{\"themes\": \"list[{{\"theme\": \"str\", \"definition\": \"str\"}}]\""

        Examples for output_schema:
        For primitive types, the output_schema can be the same as the type:
        - "output_schema": "str" for a string
        - "output_schema": "int" for an integer
        - "output_schema": "float" for a floating point number
        - "output_schema": "bool" for a boolean

        For complex types, the value of keys in output_schema should define the structure:
        - For a list of strings: "list[str]"
        - For a list of objects: "list[{{\"field1\": \"str\", \"field2\": \"int\"}}]"
        - For a dictionary: "{{\"key1\": \"str\", \"key2\": \"int\"}}"

        Examples of output_schema definitions:
        1. Simple text content:
           "output_schema": "{{ \"content\": \"str\"}}

        2. A list of tags:
           "output_schema": "{{ \"tags\": \"list[str]\" }}

        3. A person record:
           "output_schema": "{{ \"record\": \" {{\"name\": \"str\", \"age\": \"int\", \"email\": \"str\"}} \" }}"

        4. A collection of documents:
           "output_schema": "{{\"documents\": \"list[{{\"content\": \"str\", \"timestamp\": \"str\", \"author\": \"str\"}}]\"}}"

        5. Analytics results:
           "output_schema": "{{\"results\": \"{{\"total_count\": \"int\", \"average_score\": \"float\", \"categories\": \"list[str]\"}}\"}}"

        Combine the prompt and output_schema into one JSON output. The output JSON format should be a dictionary with only two keys, "prompt" and "output_schema", and the value can be any structure.
        Reply with this JSON format:
            {{
               "prompt": {{
                    "Context": str,
                    "Task": str,
                    "Requirements": str
                    "JSON_format": str // Object str with one key
                }},
                "output_schema": str  // Using the clearer schema format described above
            }}
        """.format(
            existing_keys=input_keys_str, all_keys_str=all_keys_str
        ),
    )
    task_message = f"""
        <task_name> {task['label']} </task_name>
        <description> {task['description']} </description>
        <explanation> {task['explanation']} </explanation>
    """

    # Use the new retry_llm_json_extraction function
    result = await retry_llm_json_extraction(
        llm_call_func=prompt_generation_agent.on_messages,
        llm_call_args=([TextMessage(content=task_message, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        max_retries=5,
        retry_delay=1.0,
        backoff_factor=2.0,
        escape_JSON_format=True,  # Enable escaping JSON format which is common in prompts
    )

    # If we couldn't get a valid result after all retries, return a simple fallback
    if result is None:
        return {
            "prompt": {
                "Context": f"Analyze the following {task['label']} task",
                "Task": task["description"],
                "Requirements": "Provide a detailed analysis",
                "JSON_format": '{"result": "str"}',
            },
            "output_schema": "str",
        }

    return result


async def run_input_key_generation_agent(
    task: Node, model: str, api_key: str, single_key_only=False, keys_by_state=None
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

    # Additional instruction for single key mode
    single_key_instruction = ""
    if single_key_only:
        single_key_instruction = "You MUST select EXACTLY ONE key, the most important one needed for this task."

    prompt_generation_agent = AssistantAgent(
        name="input_key_generation_agent",
        model_client=model_client,
        system_message=f"""
        ** Context **
        You are an expert in data schema design and text analytics.
        ** Task **
        The user will describe a task for you, and what data is available in the dataset. Your task is to pick the keys that are required from the dataset to complete the task, along with their detailed schema definition.
        The keys will be grouped by their state, and you must select keys only from ONE state.
        ** Requirements **
        You MUST only select keys inside the <state></state> block from the <existing_keys></existing_keys> block. No additional keys outside this list can be used. All selected keys should belong to the same state.
        {single_key_instruction}
        Reply with this JSON format, the output should be JSON compatible, you should not include any comments in the reply!:
            {{
               "required_keys": [
                   {{
                       "key": str,
                       "schema": str or object
                   }}
               ]
            }}
        
        For each key, provide a detailed schema definition that describes the exact structure.
        
        For primitive types, the schema can be the same as the type:
        - "schema": "str" for a string
        - "schema": "int" for an integer
        - "schema": "float" for a floating point number
        - "schema": "bool" for a boolean
        
        For complex types, the schema should define the structure:
        - For a list of strings: "schema": "list[str]"
        - For a list of objects: "schema": "list[dict]" or "list[{{\\"field1\\": \\"str\\", \\"field2\\": \\"int\\"}}]"
        - For a dictionary: "schema": "dict" or "{{\\"key1\\": \\"str\\", \\"key2\\": \\"int\\"}}"
        
        Examples of schema definitions:
        1. Simple text content:
           {{"key": "content", "schema": "str"}}
           
        2. A list of tags:
           {{"key": "tags", "schema": "list[str]"}}
           
        3. A person record:
           {{"key": "person", "schema": "{{\\"name\\": \\"str\\", \\"age\\": \\"int\\", \\"email\\": \\"str\\"}}"}}
           
        4. A collection of documents:
           {{"key": "documents", "schema": "list[{{\\"content\\": \\"str\\", \\"timestamp\\": \\"str\\", \\"author\\": \\"str\\"}}]"}}
           
        5. Analytics results:
           {{"key": "stats", "schema": "{{\\"total_count\\": \\"int\\", \\"average_score\\": \\"float\\", \\"categories\\": \\"list[str]\\"}}"}}
        """,
    )

    # Format the existing keys to include detailed schema information
    existing_keys_str = get_existing_keys_by_state(keys_by_state)

    task_message = f"""
        <task_name> {task['label']} </task_name>
        <description> {task['description']} </description>
        <explanation> {task['explanation']} </explanation>
        <existing_keys> {existing_keys_str} </existing_keys>
        
        Please provide detailed schema definitions for each key, not just basic types. 
        For complex structures, define the exact fields and their types in the schema.
    """
    # response = await prompt_generation_agent.on_messages(
    #     [TextMessage(content=task_message, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    # return extract_json_content(response.chat_message.content)["required_keys"]
    return await retry_llm_json_extraction(
        llm_call_func=prompt_generation_agent.on_messages,
        llm_call_args=([TextMessage(content=task_message, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        expected_key="required_keys",
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
        escape_JSON_format=True,
    )


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
    # ** Requirements **
    # The JSON format should match the unit that the user wants to evaluate.
    # Reply the evaluator specification with this JSON format. Do not wrap the json codes in JSON markers. Do not include any comments.
    # Wrap the types of the values in the JSON format with single quotes.
    prompt_generation_agent = AssistantAgent(
        name="input_key_generation_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in generating LLM judges. An LLM judge is an agent that can generate a score using some criteria.
        ** Task **
        The user will describe a text analysis task that he/she has done on a list of documents, and how he/she wants the llm judge to evaluate the task result of each document. Your task is to generate a specification of the LLM judge.
        The LLM judge should do the following:
            First, identify what the user wants to evaluate on each document. 
            Then, for each document, output a categorical score using the user-specified criteria.
        ** Requirements **
        In the LLM judge's prompt template, specify that the LLM judge must generate only **ONE** score for each document.
        Each score in "Possible Scores" should be a single word or at most a short noun-phrase.
        Reply the evaluator specification with this JSON format. Do not wrap the json codes in JSON markers. Do not include any comments.
            {{
                "evaluator_specification": {{
                    "name": str,
                    "definition": str,
                    "prompt_template": {{
                            "Context": str,
                            "Task": str,
                            "Possible Scores": list[str]
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
    # response = await prompt_generation_agent.on_messages(
    #     [TextMessage(content=user_message, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    # return extract_json_content(response.chat_message.content)[
    #     "evaluator_specification"
    # ]
    return await retry_llm_json_extraction(
        llm_call_func=prompt_generation_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        expected_key="evaluator_specification",
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


async def run_evaluator_generation_agent(
    goal: str,
    tasks,
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
    evaluator_generation_agent = AssistantAgent(
        name="evaluator_generation_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in generating evaluation criteria for text analysis tasks.
        ** Task **
        The user will describe one text analysis task that he/she has done on a list of documents along with the overarching goal.
        Your task is to recommend up to three criteria that can be used to evaluate the task result of each document.
        ** Requirements **
        Reply with the following JSON format:
            {{
                "evaluator_descriptions": [{{
                    "name": str,
                    "description": str,
                }}]
            }}
        """,
    )

    def user_message_generator(task):
        user_message = "This is my overarching goal: " + goal + "\n"
        user_message += "Here's what I am currently doing and want to evaluate: "
        user_message += f"""
            <task_name> {task['label']} </task_name>
            <description> {task['description']} </description>
        """
        return user_message

    user_messages = [user_message_generator(task) for task in tasks]
    responses = await parallel_call_agents(evaluator_generation_agent, user_messages)
    for index, response in enumerate(responses):
        # print(response.chat_message.content)
        # print("=====================================")
        responses[index] = extract_json_content(response.chat_message.content)[
            "evaluator_descriptions"
        ]
    # responses = [
    #     extract_json_content(response.chat_message.content)["evaluator_descriptions"]
    #     for response in responses
    # ]
    return responses


async def run_data_transform_plan_agent(
    task: Node,
    input_keys: list,
    state_input_key: str,
    all_states_and_keys: dict,
    model: str,
    api_key: str,
):
    """
    Generate a data transformation plan for a task using an agent.
    Args:
        task: The task node
        input_keys: Selected keys for input with their detailed schemas
        state_input_key: Input state
        all_states_and_keys: All available states and keys
        model: The model to use
        api_key: The API key for the model
    Returns:
        A data transformation plan
    """
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

    # Convert input keys to keys_by_state format
    keys_by_state = {state_input_key: input_keys}
    input_keys_str = get_existing_keys_by_state(keys_by_state)
    all_keys_str = get_all_keys_in_states(all_states_and_keys)

    data_transform_agent = AssistantAgent(
        name="data_transform_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating data transformation plans for document processing.
        You will create a plan for transforming input data from one schema to another based on the task description by writing executable Python code.

        ** Task **
        The user will provide a description of a data transformation task along with input data (typically a list of objects) and the schema of each object in the list. 
        Your job is to create a detailed transformation plan based on this information. The transformation plan must include:
        - Operation Type: Specify the type of operation (e.g., "transform") based on the task. Default to "transform" if not otherwise specified.
        - Python Code: Provide the exact, executable Python code to perform the transformation. Ensure the code is concise, well-commented, and handles the input data correctly according to the described task.
        - Output Schema: Define the schema of the transformed data (e.g., the structure of each object in the resulting list) after applying the transformation.
                
        More specifically, when you write Python code that transforms input data according to the user's requirements. Your solution must:
        1. Parse the input data using the keys provided in the input object
        2. Implement the transformation logic as described in the task
        3. Return a JSON-serializable object (output_schema) with exactly one key, ensure that the value of the key is ALWAYS an array:
            - If your transformation produces an array, assign it directly to the key.
            - If your transformation produces a single value, wrap it in an array like: `{\"your_key\": [\"value\"]}`
            - When you choose the key name to store the results, make sure it is DISTINCT from any existing keys in the user's input keys.
        
        The "output_schema" should provide a detailed, nested description of the output structure of the Python code. The output schema format should follow the same pattern of the input schema
        ** CRITICAL: formating the output_schema **
        The key and value of output_schema should all be valid string and the output_schema should be JSON serializable.
        Examples of output_schema definitions:
        1. Simple text content:
           "output_schema": "{ \"content\": \"str\"}
        2. A list of tags:
           "output_schema": "{ \"tags\": \"list[str]\" }
        3. A person record:
           "output_schema": "{ \"record\": \" {\"name\": \"str\", \"age\": \"int\", \"email\": \"str\"} \" }"
        4. A collection of documents:
           "output_schema": "{\"documents\": \"list[{\"content\": \"str\", \"timestamp\": \"str\", \"author\": \"str\"}]\"}"
        5. Analytics results:
           "output_schema": "{\"results\": \"{\"total_count\": \"int\", \"average_score\": \"float\", \"categories\": \"list[str]\"}\"}"
                
        ** IMPORTANT: Input and Output Schema Interpretation **
        When interpreting schemas, follow these rules carefully:
        1. A schema like "list[str]" means the field is an ARRAY OF STRINGS
        2. A schema like "list[dict]" or "list[{\"name\": \"str\", \"value\": \"int\"}]" means the field is an ARRAY OF OBJECTS
        3. A schema like "dict" or "{\"name\": \"str\", \"age\": \"int\"}" means the field is a SINGLE OBJECT
        
        When accessing these in Python code (assume the key is defined as `field_name`):
        - For schema "list[str]": Access directly as array, e.g., `doc["field_name"]` (returns an array)
        - For schema "list[dict]": Access directly as array of objects, e.g., `doc["field_name"]` (returns an array of objects)
        - For schema  "dict": Access as object, e.g., `doc["field_name"]` (returns an object)
        
        ** CRITICAL: Variable Scope and Data Structure **
        The transform function ALWAYS receives a parameter named 'data', which is a LIST of document objects. You MUST iterate through this list explicitly.
        
        KEY POINTS TO REMEMBER:
        1. 'data' is a LIST - you must iterate through it to access individual documents
        2. Each document in 'data' is accessed within a loop, e.g., 'for doc in data: ...'
        3. NEVER use 'doc' outside of a loop context - it will be undefined!
        4. If you need to access any document field, you MUST first establish the 'doc' variable in a loop
        
        COMMON ERRORS TO AVOID:
        WRONG: def transform(data): return {'result': doc['content']}  # ERROR: 'doc' is undefined!
        WRONG: def transform(data): return {'result': [doc['content'] for item in data]}  # ERROR: 'doc' is undefined!
        WRONG: def transform(data): return {'result': data['content']}  # ERROR: 'data' is a list, not a dict!
        
        CORRECT PATTERNS:
        CORRECT: def transform(data): return {'result': [doc['content'] for doc in data]}
        CORRECT: 
        def transform(data): 
            results = []
            for doc in data:
                results.append(doc['content'])
            return {'result': results}
        
        ** IMPORTANT: Requirement for the generated transformation Python code **
        When you generate the Python code, you have to double check it can be run without any potential issues or undefined variables.
        For example, this code is NOT ACCEPTABLE: "def transform(data): return { 'result': doc['content'] }"
        because in 'result': doc['content'], doc is not defined.

        ** Note **
        When you generate the parameters (i.e. transform_code), make sure the variables used in the code or template match the chosen input keys with its detailed schemas.
        
        ** IMPORTANT: Available Operations **
        You MUST choose "transform" as the operation - no other operations are supported.
        definition of "transform" operation - Transform the given data to another schema
           - Required parameters: 
              - "transform_code": Python code that defines a transform function, this function must be executable without any errors 
           - The function must:
             - Be named "transform"
             - Take a "data" parameter (list of documents, each document is a dictionary with all the given input keys)
             - Return transformed "data", based on user's requirements. The transformed data should be an object.
           - Also output a "output_schema" field: Detailed schema of the output structure as described before, also include your selected output key in the schema.
           - Example: to transform documents to a complex aggregated result:
```
Input keys and schema:
"teacher": "list[{'name': 'str', 'department': 'str', 'salary': 'int', 'skills': 'list[str]'}]"
"department": "{'name': 'str', 'total_students': 'int'}"

This means:
- doc["teacher"] is an ARRAY of objects, each with name, department, salary, and skills properties
- doc["department"] is a SINGLE OBJECT with name and total_students properties

CORRECT transform_code:
"transform_code": "def transform(data): return {\\n    \\"summary\\": {\\n        \\"total_salary\\": sum(t[\\"salary\\"] for doc in data for t in doc[\\"teacher\\"]),\\n        \\"total_students\\": sum(doc[\\"department\\"][\\"total_students\\"] for doc in data)\\n    }\\n}"

Example 2:
Input keys and schema:
"quotes": "list[str]", 
"summary": "list[str]"

This means:
- doc["quotes"] is an ARRAY of strings
- doc["summary"] is an ARRAY of strings

CORRECT transform_code:
"transform_code": "def transform(data): return { 'bullet_points': [item for doc in data for item in (doc.get('quotes', []) + doc.get('summary', []))] }"

Example 3 - Fix for the error in the example:
INCORRECT: 
"transform_code": "def transform(data): return { 'bullet_points': [doc['content']] + [item for doc in data for item in doc.get('quotes', [])] }"

CORRECTED:
"transform_code": "def transform(data): return { 'bullet_points': [doc['content'] for doc in data] + [item for doc in data for item in doc.get('quotes', [])] }"
```

        ** FINAL VERIFICATION STEP **
        Before finalizing your response, validate your code by:
        1. Ensuring all variables are properly defined before use
        2. Confirming that 'doc' is only used within loops iterating over 'data'
        3. Checking that your code follows the correct patterns shown above
        
        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "operation": "transform",
            "parameters": {
                "transform_code": str
            },
            "output_schema": str
        }
        """,
    )

    # data = [
    #     {
    #         "teacher": [
    #             {
    #             "name": "t1",
    #             "department": "d1",
    #             "salary": 100
    #             },
    #             {
    #                 "name": "t2",
    #                 "department": "d1",
    #                 "salary": 200
    #             },
    #         ],
    #         "department": {
    #             "name": "d1",
    #             "total_students": 1000
    #         }
    #     },
    # {
    #         "teacher": [
    #             {
    #             "name": "t3",
    #             "department": "d2",
    #             "salary": 100
    #             },
    #             {
    #                 "name": "t4",
    #                 "department": "d1",
    #                 "salary": 200
    #             },
    #         ],
    #         "department": {
    #             "name": "d2",
    #             "total_students": 10000
    #         }
    #     }
    # ]
    # Format input keys with their detailed schema information
    # input_keys_str = get_existing_keys_by_state(existing_keys)

    user_message_content = f"""
    I need to create a data transformation for the following task:

    Task: {task['label']}
    Description: {task['description']}

    Available input keys you should use with their detailed schemas: {input_keys_str}
    
    When you choose the key name to store the results in output_schema, make sure it is DISTINCT from any following existing keys in the system: {all_keys_str}

    Please generate a data transformation plan that best addresses this task. 
    Remember to:
    1. Include all required parameters including a detailed output_schema
    2. Consider the detailed schemas of input keys when creating transformations
    3. Define precise schemas for all output data structures
    """

    # response = await data_transform_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    #
    # return extract_json_content(response.chat_message.content)

    return await retry_llm_json_extraction(
        llm_call_func=data_transform_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


async def run_clustering_plan_agent(
    task: Node,
    input_keys: list,
    state_input_key: str,
    all_states_and_keys: dict,
    model: str,
    api_key: str,
):
    """
    Generate a clustering plan for a task using an agent.
    Args:
        task: The task node
        input_keys: Keys available for input with their detailed schemas
        state_input_key: Input state,
        model: The model to use
        api_key: The API key for the model
    Returns:
        A clustering plan configuration
    """
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
    clustering_agent = AssistantAgent(
        name="clustering_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating clustering plans for document analysis.
        You will create a configuration for clustering documents based on the task description.

        ** Task **
        The user will describe a clustering task. You need to create a clustering configuration
        that includes the algorithm to use and the parameters for that algorithm.
        You need to carefully select the parameters for clustering based on the input data schema provided by the user.

        Also, you also need to determine the key for "output_schema" to define the clustering output. 
        The "output_schema" should be a JSON-serializable object string with exactly one key you selected, ensure that the value of the key is ALWAYS "int"
        IMPORTANT: When you choose the key name in output_schema, make sure it is DISTINCT from any existing keys in the user's input keys.  
        ** Note **
        The input data needs to contain embeddings (vector representations) for effective clustering.

        ** IMPORTANT: Available Clustering Algorithms **
        Choose ONE of these algorithms based on the task requirements:

        1. kmeans - K-means clustering (preferred, requires number of clusters)
           - Good for: Simple clustering with roughly equal-sized, well-separated clusters
           - Parameters:
             - n_clusters: Number of clusters (required, integer)
             - init: Initialization method ('k-means++' or 'random')
             - n_init: Number of initializations to try
             - max_iter: Maximum number of iterations

        2. dbscan - Density-Based Spatial Clustering (doesn't require number of clusters)
           - Good for: Finding clusters of arbitrary shape, handling noise/outliers
           - Parameters:
             - eps: Maximum distance between samples for neighborhood
             - min_samples: Minimum number of samples in a neighborhood
             - metric: Distance metric to use

        3. agglomerative - Hierarchical clustering
           - Good for: Finding hierarchical relationships, generating dendrograms
           - Parameters:
             - n_clusters: Number of clusters (required, integer)
             - linkage: Linkage criterion ('ward', 'complete', 'average', or 'single')
             - affinity: Distance metric to use

        4. gaussian_mixture - Gaussian Mixture Model
           - Good for: Soft clustering with probability distributions
           - Parameters:
             - n_components: Number of mixture components (required, integer)
             - covariance_type: Type of covariance ('full', 'tied', 'diag', 'spherical')
             - max_iter: Maximum number of iterations

        5. hdbscan - Hierarchical DBSCAN
           - Good for: Finding clusters of varying densities, robust to noise
           - Parameters:
             - min_cluster_size: Minimum size for a cluster
             - min_samples: Minimum number of samples in neighborhood
             - cluster_selection_epsilon: Distance threshold for cluster formation

        6. bertopic - BERTopic (uses transformer models with UMAP+HDBSCAN)
           - Good for: Topic modeling and clustering of text documents
           - Parameters:
             - min_topic_size: Minimum size for a topic
             - n_neighbors: Number of neighbors for UMAP
             - low_memory: Lower memory usage but slower (True/False)
        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "algorithm": "kmeans" | "dbscan" | "agglomerative" | "gaussian_mixture" | "hdbscan" | "bertopic",
            "parameters": {
                // Parameters specific to the chosen algorithm
            },
            "output_schema": "{ '<your generated output key>': 'int'}"
        }
        """,
    )

    # Convert input keys to keys_by_state format
    keys_by_state = {state_input_key: input_keys}
    input_keys_str = get_existing_keys_by_state(keys_by_state)
    all_keys_str = get_all_keys_in_states(all_states_and_keys)

    user_message_content = f"""
    I need to create a clustering plan for the following task:

    Task: {task['label']}
    Description: {task['description']}

    The input key you should use with its detailed schema: {input_keys_str}
    
    When you choose the key name to store the results in output_schema, make sure it is DISTINCT from any following existing keys in the system: {all_keys_str}

    Please generate a clustering configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate clustering algorithm for the task
    2. Specify all required parameters for that algorithm
    3. Decide if evaluation metrics should be returned
    4. Define the output_schema by picking a reasonable output key.
    """

    # response = await clustering_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    #
    # return extract_json_content(response.chat_message.content)

    return await retry_llm_json_extraction(
        llm_call_func=clustering_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


async def run_dim_reduction_plan_agent(
    task: Node,
    input_keys: list,
    state_input_key: str,
    all_states_and_keys: dict,
    model: str,
    api_key: str,
):
    """
    Generate a dimensionality reduction plan for a task using an agent.
    Args:
        task: The task node
        input_keys: Keys available for input with their detailed schemas
        state_input_key: Input state
        model: The model to use
        api_key: The API key for the model
    Returns:
        A dimensionality reduction plan configuration
    """
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
    dim_reduction_agent = AssistantAgent(
        name="dim_reduction_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating dimensionality reduction plans for data visualization and analysis.
        You will create a configuration for reducing the dimensions of data based on the task description.

        ** Task **
        The user will describe a dimensionality reduction task. You need to create a configuration
        that includes the algorithm to use and the parameters for that algorithm.
        
        You need to carefully select the parameters for dimensionality reduction based on the input data schema provided by the user.

        Also, you also need to determine the key for "output_schema" to define the dimensionality reduction output. 
        The "output_schema" should be a JSON-serializable object string with exactly one key you selected, ensure that the value of the key is ALWAYS "list[float]"
        IMPORTANT: When you choose the key name in output_schema, make sure it is DISTINCT from any existing keys in the user's input keys.
          
        ** Note **
        The input data needs to contain high-dimensional embeddings that need to be reduced to lower dimensions.
        You need to specify the number of dimensions to reduce to based on your understanding on user's input data schema and the provided use case.

        ** IMPORTANT: Available Dimensionality Reduction Algorithms **
        Choose ONE of these algorithms based on the task requirements:

        1. pca - Principal Component Analysis
           - Good for: Linear dimensionality reduction, preserving global structure
           - Fast, but may not capture non-linear relationships
           - Parameters:
             - n_components: Number of dimensions to reduce to (required, integer)
             - whiten: Whether to whiten the data (boolean)

        2. tsne - t-distributed Stochastic Neighbor Embedding
           - Good for: Non-linear dimensionality reduction, preserving local structure
           - Better for visualization but computationally intensive
           - Parameters:
             - n_components: Number of dimensions to reduce to (required, integer)
             - perplexity: Related to number of nearest neighbors (default 30)
             - early_exaggeration: Control early clustering (default 12)
             - learning_rate: Learning rate (default 200)

        3. umap - Uniform Manifold Approximation and Projection
           - Good for: Non-linear dimensionality reduction with better global structure than t-SNE
           - Fast and effective for visualization and machine learning
           - Parameters:
             - n_components: Number of dimensions to reduce to (required, integer)
             - n_neighbors: Size of local neighborhood (default 15)
             - min_dist: Minimum distance between points (default 0.1)
             - metric: Distance metric to use (default 'euclidean')
        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "algorithm": "pca" | "tsne" | "umap",
            "parameters": {
                "n_components": int,  // Number of dimensions to reduce to (typically 2 or 3 for visualization)
                // Additional algorithm-specific parameters
            },
            "output_schema": "{ '<your generated output key>': 'list[float]'}"
        }
        """,
    )

    # Convert input keys to keys_by_state format
    if len(input_keys) > 1:
        input_keys = input_keys[:1]
    keys_by_state = {state_input_key: input_keys}
    input_keys_str = get_existing_keys_by_state(keys_by_state)
    all_keys_str = get_all_keys_in_states(all_states_and_keys)

    user_message_content = f"""
    I need to create a dimensionality reduction plan for the following task:

    Task: {task['label']}
    Description: {task['description']}

    The input key you should use with its detailed schema: {input_keys_str}
    
    When you choose the key name to store the results in output_schema, make sure it is DISTINCT from any following existing keys in the system: {all_keys_str}

    Please generate a dimensionality reduction configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate dimensionality reduction algorithm for the task
    2. Specify all required parameters for that algorithm
    3. Define the number of components to reduce to
    4. Define the output_schema by picking a reasonable output key.
    """

    # response = await dim_reduction_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    #
    # return extract_json_content(response.chat_message.content)
    return await retry_llm_json_extraction(
        llm_call_func=dim_reduction_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


async def run_embedding_plan_agent(
    task: Node,
    input_keys: list,
    state_input_key: str,
    all_states_and_keys: dict,
    model: str,
    api_key: str,
):
    """
    Generate an embedding plan for a task using an agent.
    Args:
        task: The task node
        input_keys: Keys available for input with their detailed schemas
        model: The model to use
        api_key: The API key for the model
    Returns:
        An embedding plan configuration
    """
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
    embedding_agent = AssistantAgent(
        name="embedding_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in creating embedding plans for text data.
        You will create a configuration for generating vector embeddings based on the task description.

        ** Task **
        The user will describe an embedding task. You need to create a configuration
        that includes the embedding model to use and the parameters for that model.

        You need to carefully select the parameters for embedding based on the input data schema provided by the user.

        Also, you also need to determine the key for "output_schema" to define the embedding output. 
        The "output_schema" should be a JSON-serializable object string with exactly one key you selected, ensure that the value of the key is ALWAYS "list[float]"
        IMPORTANT: When you choose the key name in output_schema, make sure it is DISTINCT from any existing keys in the user's input keys.
          
        ** Note **
        Embeddings convert text into dense vector representations that capture semantic meaning.

        ** IMPORTANT: Available Embedding Providers and Models **
        Choose a provider and model combination based on the task requirements:

        1. openai - OpenAI's embedding models
           - Models: "text-embedding-ada-002" (default), "text-embedding-3-small", "text-embedding-3-large"
           - Good for: High-quality embeddings, semantic search, clustering
           - Requires API key
           - Parameters:
             - model: The embedding model to use (string)

        2. sentence_transformers - Local embedding models using Sentence Transformers
           - Models: "all-MiniLM-L6-v2" (default), "all-mpnet-base-v2", "paraphrase-multilingual-MiniLM-L12-v2"
           - Good for: Local processing without API calls, multilingual support
           - No API key required
           - Parameters:
             - model: The embedding model to use (string)
        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "provider": "openai" | "sentence_transformers",
            "parameters": {
                "model": str,  // Embedding model to use
                // Any additional parameters specific to the provider
            },
            "output_schema": "{ '<your generated output key>': 'list[float]'}"
        }
        """,
    )

    # Convert input keys to keys_by_state format
    if len(input_keys) > 1:
        input_keys = input_keys[:1]
    keys_by_state = {state_input_key: input_keys}
    input_keys_str = get_existing_keys_by_state(keys_by_state)
    all_keys_str = get_all_keys_in_states(all_states_and_keys)

    user_message_content = f"""
    I need to create an embedding plan for the following task:

    Task: {task['label']}
    Description: {task['description']}

    The input key you should use with its detailed schema: {input_keys_str}
    
    When you choose the key name to store the results in output_schema, make sure it is DISTINCT from any following existing keys in the system: {all_keys_str}

    Please generate an embedding configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate embedding provider for the task
    2. Select a suitable embedding model
    3. Define the output_schema by picking a reasonable output key.
    4. Consider whether API access is available or if local processing is needed
    """

    # response = await embedding_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    #
    # return extract_json_content(response.chat_message.content)
    return await retry_llm_json_extraction(
        llm_call_func=embedding_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


async def run_segmentation_plan_agent(
    task: Node,
    input_keys: list,
    state_input_key: str,
    all_states_and_keys: dict,
    model: str,
    api_key: str,
):
    """
    Generate a segmentation plan for a task using an agent.
    Args:
        task: The task node
        input_keys: Keys available for input with their detailed schemas
        state_input_key: Input state
        model: The model to use
        api_key: The API key for the model
    Returns:
        A segmentation plan configuration
    """
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
    segmentation_agent = AssistantAgent(
        name="segmentation_plan_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are an expert in text segmentation for document processing.
        You will create a configuration for segmenting text documents based on the task description.        

        ** Task **
        The user will describe a segmentation task. You need to create a configuration
        that includes the segmentation strategy and the parameters for that strategy.

        You need to carefully select the parameters for segmentation based on the input data schema provided by the user.

        Also, you also need to determine the key for "output_schema" to define the segmentation output. 
        The "output_schema" should be a JSON-serializable object string with exactly one key you selected, ensure that the value of the key is ALWAYS "list[str]"
        IMPORTANT: When you choose the key name in output_schema, make sure it is DISTINCT from any existing keys in the user's input keys.
          

        ** Note **
        Text segmentation divides long documents into smaller, manageable chunks.

        ** IMPORTANT: Available Segmentation Strategies **
        Choose ONE of these strategies based on the task requirements:

        1. paragraph - Split text by paragraphs
           - Good for: Natural document structure, preserving paragraph meaning
           - Simple and effective for well-formatted documents
           - Parameters: None

        2. sentence - Split text by sentences
           - Good for: Fine-grained analysis, shorter segments
           - Uses NLTK's sentence tokenizer
           - Parameters: None

        3. fixed_length - Split text into chunks of specified length
           - Good for: Creating uniform-sized chunks
           - Allows for overlapping chunks to preserve context
           - Parameters:
             - chunk_size: Maximum number of characters per chunk (default: 100)
             - overlap: Number of overlapping characters between chunks (default: 10)

        4. semantic - Split text based on semantic meaning
           - Good for: Creating semantically coherent chunks
           - Uses embeddings to detect topic shifts
           - Parameters:
             - threshold: Similarity threshold for boundary detection (default: 0.5)
             - model: Optional model to use for embeddings (default: depends on availability)
             - api_key: API key for embedding model (if required)
        ** Response Format **
        You MUST respond with a JSON object in this exact format:
        {
            "strategy": "paragraph" | "sentence" | "fixed_length" | "semantic",
            "parameters": {
                // Additional strategy-specific parameters
            },
            "output_schema": "{ '<your generated output key>': 'list[str]'}"
        }
        """,
    )

    # Convert input keys to keys_by_state format
    if len(input_keys) > 1:
        input_keys = input_keys[:1]
    keys_by_state = {state_input_key: input_keys}
    input_keys_str = get_existing_keys_by_state(keys_by_state)
    all_keys_str = get_all_keys_in_states(all_states_and_keys)

    user_message_content = f"""
    I need to create a segmentation plan for the following task:

    Task: {task['label']}
    Description: {task['description']}

    The input key you should use with its detailed schema: {input_keys_str}
    
    When you choose the key name to store the results in output_schema, make sure it is DISTINCT from any following existing keys in the system: {all_keys_str}

    Please generate a segmentation configuration that best addresses this task. 
    Remember to:
    1. Choose the most appropriate segmentation strategy for the task
    2. Specify all required parameters for that strategy
    3. Define the output_schema by picking a reasonable output key.
    """

    # response = await segmentation_agent.on_messages(
    #     [TextMessage(content=user_message_content, source="user")],
    #     cancellation_token=CancellationToken(),
    # )
    #
    # return extract_json_content(response.chat_message.content)
    return await retry_llm_json_extraction(
        llm_call_func=segmentation_agent.on_messages,
        llm_call_args=([TextMessage(content=user_message_content, source="user")],),
        llm_call_kwargs={"cancellation_token": CancellationToken()},
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
    )


def get_existing_keys_by_state(keys_by_state):
    """
    Format keys grouped by state for the LLM prompt.

    Args:
        keys_by_state: Dictionary mapping state names to lists of keys

    Returns:
        Formatted string with keys organized by state
    """
    states_info = []
    for state_name, keys in keys_by_state.items():
        keys_str = get_existing_keys_and_schema(keys)
        states_info.append(f'<state name="{state_name}">\n{keys_str}\n</state>')

    return "\n".join(states_info) if states_info else "No states available."


def get_all_keys_in_states(keys_by_state):
    """
    Extract all keys from all states in the keys_by_state dictionary and return as a comma-separated string.

    Args:
        keys_by_state: Dictionary mapping state names to lists of keys

    Returns:
        String of all key names across all states, separated by commas
    """
    all_keys = []

    # If keys_by_state is None or empty, return an empty string
    if not keys_by_state:
        return ""

    # Iterate through all states and their keys
    for state_name, keys in keys_by_state.items():
        for key_obj in keys:
            # Keys can be strings or dictionaries with a 'key' field
            if isinstance(key_obj, dict) and "key" in key_obj:
                all_keys.append(key_obj["key"])
            elif isinstance(key_obj, str):
                all_keys.append(key_obj)

    # Convert the list of keys to a comma-separated string
    return ",".join(all_keys)


def get_existing_keys_and_schema(existing_keys):
    # Format the existing keys to include detailed schema information
    formatted_keys = []
    for key in existing_keys:
        if isinstance(key, dict):
            if "key" in key and "schema" in key:
                # Convert any JSON Schema format to the clearer format if needed, in case LLM returns a JSON Schema
                schema = key["schema"]
                if isinstance(schema, dict):
                    if "items" in schema:
                        if isinstance(schema["items"], dict):
                            # Convert {"items": {"field1": "str", ...}} to "list[{'field1': 'str', ...}]"
                            items_dict = str(schema["items"]).replace('"', "'")
                            schema = f"list[{items_dict}]"
                        else:
                            # Convert {"items": "str"} to "list[str]"
                            schema = f"list[{schema['items']}]"
                    elif "properties" in schema:
                        # Convert {"properties": {"field1": "str", ...}} to "{'field1': 'str', ...}"
                        props_dict = str(schema["properties"]).replace('"', "'")
                        schema = props_dict

                formatted_keys.append(f"{key['key']} (schema: {schema})")
            elif "key" in key:
                formatted_keys.append(
                    f"{key['key']} (schema: str)"
                )  # default to use str for prompt tools
        elif isinstance(key, str):
            formatted_keys.append(f"{key} (schema: str)")

    return ", ".join(formatted_keys) if formatted_keys else str(existing_keys)