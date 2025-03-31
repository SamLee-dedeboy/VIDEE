<script lang="ts">
  import { server_address } from "constants";
  import { onMount, setContext, tick } from "svelte";
  import type {
    tExecutionEvaluator,
    tPrimitiveTask,
    tSemanticTask,
  } from "types";
  import {
    primitiveTaskState,
    primitiveTaskExecutionStates,
    semanticTaskPlanState,
    evaluatorState,
    session_id,
    likert_scale_num,
  } from "lib/ExecutionStates.svelte";
  import GoalInput from "lib/Searching/GoalInput.svelte";
  import SemanticTaskTreeInspection from "lib/Inspection/SemanticTaskTreeInspection.svelte";
  import ExecutionInspection from "lib/Inspection/ExecutionInspection.svelte";
  import Execution from "lib/Execution/Execution.svelte";
  import SemanticTasksTree from "lib/Searching/SemanticTasksTree.svelte";
  let decomposing_goal = $state(false);

  // stream states
  let streaming_states = $state({
    started: false,
    paused: false,
    finished: false,
  });
  let controllers: {
    converting: boolean;
    compiling: boolean | string | undefined;
  } = $state({
    converting: false,
    compiling: false,
  });
  let stream_controller: any = $state(undefined);
  let mode = $state("step");

  let semantic_tasks: tSemanticTask[] = $state([]);
  let next_expansion: tSemanticTask | undefined = $state(undefined);
  let select_strategy: string = $derived(semanticTaskPlanState.select_strategy);
  let selected_semantic_task_path: tSemanticTask[] = $state([]);
  $effect(() => {
    semanticTaskPlanState.semantic_tasks = selected_semantic_task_path;
  });
  let few_shot_examples_semantic_tasks: Record<string, any> = $state({});

  let user_goal: string = $state("");

  let primitive_tasks = $derived(primitiveTaskState.primitiveTasks);
  let inspected_primitive_task = $derived(
    primitiveTaskState.inspected_primitive_task
  );
  let inspected_evaluator_node = $derived(
    evaluatorState.inspected_evaluator_node
  );
  // let inspected_evaluator_node: tExecutionEvaluator | undefined = $state(undefined);

  let execution_panel: any = $state();
  let execution_inspection_panel: any = $state();

  /**
   * Stores the state of the dag
   * @value mcts | execution
   */
  let show_dag = $state("mcts");

  /**
   * updates the few shot examples every time semantic tasks are updated
   */
  function updateFewShotExamples() {
    const evaluations = ["complexity", "coherence", "importance"];
    console.log(
      "few shot examples for semantic tasks: ",
      $state.snapshot(semantic_tasks)
    );
    semantic_tasks.forEach((task) => {
      evaluations.forEach((evaluation) => {
        if (
          task.user_evaluation[evaluation] !== task.llm_evaluation[evaluation]
        ) {
          if (!few_shot_examples_semantic_tasks[evaluation])
            few_shot_examples_semantic_tasks[evaluation] = [];
          const example_index = few_shot_examples_semantic_tasks[
            evaluation
          ].findIndex((t) => t.node.label === task.label);
          if (example_index === -1) {
            few_shot_examples_semantic_tasks[evaluation].push({
              node: task,
              parent_node: semantic_tasks.find(
                (t) => t.MCT_id === task.MCT_parent_id
              ),
              user_evaluation: task.user_evaluation[evaluation],
              llm_evaluation: task.llm_evaluation[evaluation],
              user_reasoning: undefined,
            });
          } else {
            few_shot_examples_semantic_tasks[evaluation][example_index] = {
              node: task,
              parent_node: semantic_tasks.find(
                (t) => t.MCT_id === task.MCT_parent_id
              ),
              user_evaluation: task.user_evaluation[evaluation],
              llm_evaluation: task.llm_evaluation[evaluation],
              user_reasoning:
                few_shot_examples_semantic_tasks[evaluation][example_index]
                  .user_reasoning,
            };
          }
        } else {
          if (few_shot_examples_semantic_tasks[evaluation]) {
            const example_index = few_shot_examples_semantic_tasks[
              evaluation
            ].findIndex((t) => t.node.label === task.label);
            if (example_index !== -1) {
              few_shot_examples_semantic_tasks[evaluation].splice(
                example_index,
                1
              );
            }
          }
        }
      });
    });
    console.log(
      "few shot examples: ",
      $state.snapshot(few_shot_examples_semantic_tasks)
    );
    few_shot_examples_semantic_tasks = { ...few_shot_examples_semantic_tasks };
  }

  function setFewShotExampleExplanation(
    task: tSemanticTask,
    evaluation: string,
    user_reasoning: string
  ) {
    console.log({
      task,
      evaluation,
      user_reasoning,
      few_shot_examples_semantic_tasks: $state.snapshot(
        few_shot_examples_semantic_tasks
      ),
    });
    const example_index = few_shot_examples_semantic_tasks[evaluation]
      .map((t) => t.node.MCT_id)
      .indexOf(task.MCT_id);
    console.log({ example_index });
    if (example_index !== -1) {
      few_shot_examples_semantic_tasks[evaluation][
        example_index
      ].user_reasoning = user_reasoning;
    }
  }
  setContext("setFewShotExampleExplanation", setFewShotExampleExplanation);

  async function init() {
    await fetchTest();
    await createSession();
    // await fetchStream();
  }

  function fetchTest() {
    fetch(`${server_address}/test/`)
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function createSession() {
    // let random_session_id = Math.random().toString(36).substring(2, 15);
    // let random_session_id = "312321321312321";
    fetch(`${server_address}/session/create/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id: session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        // session_id = data.session_id;
        console.log("Session created:", session_id);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
  async function dev_handleDecomposeGoalStepped_MCTS(goal: string) {
    fetch(`${server_address}/dev/semantic_task/plan/`)
      .then((response) => response.json())
      .then((obj) => {
        console.log({ obj });
        semantic_tasks = Object.values(obj["node_dict"]) as any[];
        next_expansion = obj["next_node"];
        selected_semantic_task_path = obj["max_value_path"][0].map(
          (id: string) => semantic_tasks.find((t) => t["MCT_id"] === id)!
        );
      });
  }

  async function handleDecomposeGoalStepped_MCTS(goal: string) {
    // dev_handleDecomposeGoalStepped_MCTS(goal);
    // return;
    user_goal = goal;
    streaming_states.started = true;
    streaming_states.paused = false;
    stream_controller = new AbortController();
    const signal = stream_controller.signal;
    try {
      const response = await fetch(
        `${server_address}/goal_decomposition/mcts/stepped/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            goal,
            session_id,
            semantic_tasks,
            next_expansion,
            eval_few_shot_examples: few_shot_examples_semantic_tasks,
            select_strategy: select_strategy,
          }),
          signal,
        }
      );
      if (!response.body) {
        throw new Error("Stream error");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete JSON objects line by line
        let lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep the last incomplete part for the next iteration

        for (let line of lines) {
          if (line) {
            const obj = JSON.parse(line);
            console.log("Received:", obj);
            semantic_tasks = Object.values(obj["node_dict"]) as any[];
            next_expansion = obj["next_node"];
            selected_semantic_task_path = obj["max_value_path"][0].map(
              (id: string) => semantic_tasks.find((t) => t["MCT_id"] === id)!
            );
            if (mode === "step" && stream_controller !== undefined) {
              stream_controller.abort(); // Stop streaming
              stream_controller = undefined;
            }
            // semantic_tasks = obj["semantic_tasks"][0][0];
          }
        }
      }
      console.log("Stream finished");
      streaming_states.started = false;
      streaming_states.paused = false;
      streaming_states.finished = true;
    } catch (error: any) {
      if (error.name === "AbortError") {
        streaming_states.paused = true;
        console.log("Stream aborted");
      } else {
        console.error("Error:", error);
        stream_controller.abort(); // Stop streaming
        stream_controller = undefined;
      }
    } finally {
      stream_controller = undefined;
    }
  }

  function handleRegenerate(task: tSemanticTask, callback = () => {}) {
    streaming_states.started = true;
    streaming_states.paused = false;
    fetch(`${server_address}/goal_decomposition/mcts/regenerate/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id,
        goal: user_goal,
        target_task: task,
        semantic_tasks,
        eval_few_shot_examples: few_shot_examples_semantic_tasks,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("task regenerated: ", { data });
        semantic_tasks = Object.values(data["node_dict"]) as any[];
        next_expansion = data["next_node"];
        selected_semantic_task_path = data["max_value_path"][0].map(
          (id: string) => semantic_tasks.find((t) => t["MCT_id"] === id)!
        );
        streaming_states.started = false;
        streaming_states.paused = false;
        callback();
      })
      .catch((error) => {
        console.error("Error:", error);
        streaming_states.started = false;
        streaming_states.paused = false;
      });
  }

  /**
   * convert the semantic tasks to primitive tasks
   */

  function handleConvert() {
    controllers.converting = true;
    // fetch(`${server_address}/semantic_task/decomposition_to_primitive_tasks/`, {
    fetch(
      `${server_address}/semantic_task/decomposition_to_primitive_tasks/dev/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ semantic_tasks: selected_semantic_task_path }),
      }
    )
      .then((response) => response.json())
      .then((data) => {
        console.log("decomposition to primitive tasks: ", { data });
        primitiveTaskState.primitiveTasks = data;
        controllers.converting = false;
        handleCompile();
      })
      .catch((error) => {
        console.error("Error:", error);
        controllers.converting = false;
      });
  }

  function handleCompile(
    task: tPrimitiveTask | undefined = undefined,
    skip_IO = false,
    skip_parameters = false
  ) {
    console.log("Compiling...", { primitive_tasks, task, session_id });
    controllers.compiling = task?.id;
    // fetch(`${server_address}/primitive_task/compile/`, {
    fetch(`${server_address}/primitive_task/compile/dev/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        primitive_tasks,
        compile_target: task?.id,
        skip_IO,
        skip_parameters,
        session_id,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        controllers.compiling = false;
        data.primitive_tasks.forEach((t) => {
          t.recompile_needed_IO = false;
          t.recompile_needed_parameters = false;
        });
        primitiveTaskState.primitiveTasks = data.primitive_tasks;
        primitiveTaskExecutionStates.execution_states = data.execution_state;
        console.log({ data });
        execution_panel.generate_evaluator_recommendations(
          data.primitive_tasks
        );
      })
      .catch((error) => {
        console.error("Error:", error);
        controllers.compiling = false;
      });
  }
  setContext("handleCompile", handleCompile);

  function handleUserFeedback(
    task_id: string,
    evaluation: string,
    value: number
  ) {
    const target_task_index = semantic_tasks
      .map((t) => t.MCT_id)
      .indexOf(task_id);
    if (target_task_index !== -1) {
      const target_task = semantic_tasks[target_task_index];
      target_task.user_evaluation[evaluation] = value;
      target_task.value =
        (+target_task.user_evaluation.complexity +
          +target_task.user_evaluation.coherence +
          +target_task.user_evaluation.importance) /
        (3 * likert_scale_num);

      semantic_tasks[target_task_index] = target_task;
      // update the path value
      const parent_task_index = semantic_tasks
        .map((t) => t.MCT_id)
        .indexOf(target_task.MCT_parent_id);
      if (parent_task_index !== -1) {
        const parent_task = semantic_tasks[parent_task_index];
        target_task.path_value = parent_task.path_value * target_task.value;
      }

      // update the children path values
      let queue = [target_task];
      while (queue.length > 0) {
        const node = queue.shift();
        node?.MCT_children_ids.forEach((child_id) => {
          const child_index = semantic_tasks
            .map((t) => t.MCT_id)
            .indexOf(child_id);
          if (child_index !== -1) {
            const child = semantic_tasks[child_index];
            child.path_value = node.path_value * child.value;
            queue.push(child);
          }
        });
      }
    }
    updateFewShotExamples();
  }
  setContext("handleUserFeedback", handleUserFeedback);

  async function playTransitionToExecution() {
    const canvas = document.querySelector(".tree-canvas");
    const overlay = document.createElement("div");
    overlay.style.position = "absolute";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.right = "0";
    overlay.style.bottom = "0";
    overlay.style.transition = "all 0.5s";
    overlay.style.zIndex = "100";
    overlay.style.backgroundColor = "#f3f3f3";

    const whole_tree = document.createElement("div");
    whole_tree.style.position = "absolute";
    whole_tree.style.top = "36px";
    whole_tree.style.left = "0";
    whole_tree.style.right = "0";
    whole_tree.style.bottom = "0";
    whole_tree.style.transition = "all 0.5s";
    whole_tree.style.zIndex = "100";

    const plan_path = document.createElement("div");
    plan_path.style.position = "absolute";
    plan_path.style.top = "36px";
    plan_path.style.left = "0";
    plan_path.style.right = "0";
    plan_path.style.bottom = "0";
    plan_path.style.zIndex = "100";

    const semantic_tasks_container = document.querySelector(".semantic-tasks");
    semantic_tasks_container?.childNodes.forEach((child) => {
      // check if the child is an element node
      if (child.nodeType !== Node.ELEMENT_NODE) return;
      const node = child as HTMLElement; // Type assertion

      // check if the node is a task card container
      if (!node.classList.contains("semantic-task-card-container")) return;

      node.classList.remove("semantic-task-card-container");
      node.classList.add("semantic-task-card-container-transition");
      whole_tree.appendChild(child.cloneNode(true));

      // check if the task card container is on the max value path
      const task_card_container: any = node.querySelector(
        ".task-card-container"
      );
      if (!task_card_container.classList.contains("on-max-value-path")) return;

      // remove root
      if (task_card_container.querySelector(".card-label").innerText === "Root")
        return;

      plan_path.appendChild(node.cloneNode(true));
    });
    overlay?.appendChild(plan_path);
    overlay?.appendChild(whole_tree);
    canvas?.appendChild(overlay);
    setTimeout(() => {
      whole_tree.style.opacity = "0";
      setTimeout(() => {
        // overlay.style.opacity = "0";
        overlay.style.backgroundColor = "transparent";
        const semantic_task_plane_nodes = document
          .querySelector(".semantic-task-plan")
          ?.querySelectorAll(".semantic-task-card-container");
        const nodes = overlay.querySelectorAll(
          ".semantic-task-card-container-transition"
        );
        nodes.forEach((node: any) => {
          const target_node = Array.from(semantic_task_plane_nodes!).filter(
            (n: any) =>
              n.querySelector(".card-label").innerText ===
              node.querySelector(".card-label").innerText
          )[0];
          if (target_node) {
            const target_bbox = target_node.getBoundingClientRect();
            // const target_transform = (target_node as HTMLElement).style
            //   .transform;
            // (node as HTMLElement).style.transform = target_transform;
            (node as HTMLElement).style.transform = "translate(-15px,-150px)";
            (node as HTMLElement).style.transition = "all linear 0.5s ease-out";
            (node as HTMLElement).style.left = `${target_bbox.x}px`;
            (node as HTMLElement).style.top = `${target_bbox.y}px`;
            (node as HTMLElement).style.opacity = "0";
          }
        });
        setTimeout(() => {
          overlay.remove();
        }, 1000);
      }, 800);
    }, 500);
  }
  onMount(() => {
    init();
  });
</script>

<main class="w-[100vw] h-[100vh] flex py-2 px-[1rem] gap-y-1">
  {#if !session_id}
    <div class="self-center">Loading...</div>
  {:else}
    <div class="flex flex-[3_3_0%] shrink-0 flex-col gap-y-2">
      <div class="bg-white flex gap-x-2">
        <GoalInput
          handleDecomposeGoal={handleDecomposeGoalStepped_MCTS}
          disable_decompose={show_dag === "execution"}
          bind:user_goal
          bind:mode
          {streaming_states}
        />
        <button
          id="stop"
          class="outline-2 outline-red-300 p-2 bg-red-100 rounded hover:bg-red-200"
          class:hidden={!(streaming_states.started && !streaming_states.paused)}
          onclick={() => {
            if (stream_controller !== undefined) {
              stream_controller.abort(); // Stop streaming
              stream_controller = undefined;
            }
          }}>Stop Streaming</button
        >
        <div class="flex">
          <button
            class="min-6-[6rem] px-2 py-1 font-mono rounded-l outline-1 outline-gray-400 text-slate-700 hover:outline-orange-300 hover:outline-2 hover:z-20 hover:!text-slate-700"
            class:disabled={streaming_states.started &&
              !streaming_states.paused}
            style={`${show_dag === "mcts" ? "background-color: oklch(0.901 0.076 70.697); opacity: 1;" : "background-color: #fafafa; color: rgba(0, 0, 0, 0.2)"}`}
            onclick={() => (show_dag = "mcts")}>Searching</button
          >
          <button
            class="min-w-[6rem] px-2 py-1 font-mono rounded-r outline-1 outline-gray-400 text-slate-700 hover:outline-blue-300 hover:outline-2 hover:z-10 hover:!text-slate-700"
            class:disabled={streaming_states.started &&
              !streaming_states.paused}
            style={`${show_dag === "execution" ? "background-color: oklch(0.882 0.059 254.128); opacity: 1;" : "background-color: #fafafa;  color: rgba(0, 0, 0, 0.2)"}`}
            onclick={() => {
              show_dag = "execution";
              playTransitionToExecution();
            }}>Execution</button
          >
        </div>
      </div>
      <div class="flex flex-[2_2_0%] gap-x-2">
        <div
          class="tree-canvas relative grow px-2 py-1"
          class:loading-canvas={streaming_states.started &&
            !streaming_states.paused}
        >
          <div
            class="absolute top-0 left-0 right-0 bottom-0 flex overflow-hidden"
          >
            {#if show_dag === "mcts"}
              <SemanticTasksTree
                {decomposing_goal}
                {handleRegenerate}
                bind:semantic_tasks
                bind:streaming_states
                bind:next_expansion
                bind:selected_semantic_task_path
              ></SemanticTasksTree>
            {:else if show_dag == "execution"}
              <Execution
                bind:this={execution_panel}
                {user_goal}
                {decomposing_goal}
                {handleConvert}
                converting={controllers.converting}
                compiling={controllers.compiling}
                handleInspectPrimitiveTask={async (
                  task,
                  show_result = false
                ) => {
                  console.log("inspecting task", task);
                  primitiveTaskState.updateInspectedPrimitiveTask(task.id);
                  evaluatorState.updateInspectedEvaluator(undefined);
                  // inspected_primitive_task = task;
                  // inspected_evaluator_node = undefined;
                  if (show_result) {
                    execution_inspection_panel.navigate_to_primitive_task_results();
                  } else {
                    execution_inspection_panel.scrollIntoInspectionPanel();
                  }
                }}
                handleInspectEvaluatorNode={async (
                  node,
                  show_result = false
                ) => {
                  console.log("inspecting evaluator", node);
                  // inspected_evaluator_node = node;
                  // inspected_primitive_task = undefined;
                  primitiveTaskState.updateInspectedPrimitiveTask(undefined);
                  evaluatorState.updateInspectedEvaluator(node.name);
                  if (show_result) {
                    execution_inspection_panel.navigate_to_evaluator_results();
                  } else {
                    execution_inspection_panel.scrollIntoInspectionPanel();
                  }
                }}
              ></Execution>
            {/if}
          </div>
        </div>
      </div>
    </div>
    <div class="inspection-panel flex-1 flex flex-col overflow-auto gap-y-2">
      {#if show_dag === "mcts"}
        <SemanticTaskTreeInspection
          few_shot_examples={few_shot_examples_semantic_tasks}
        ></SemanticTaskTreeInspection>
      {:else if show_dag === "execution"}
        <ExecutionInspection
          bind:this={execution_inspection_panel}
          primitive_task={inspected_primitive_task}
          evaluator_node={inspected_evaluator_node}
        ></ExecutionInspection>
      {/if}
    </div>
  {/if}
</main>

<style lang="postcss">
  @reference "tailwindcss";
  .disabled {
    @apply !opacity-50 pointer-events-none;
  }
  .hidden {
    @apply hidden;
  }

  .loading-canvas {
    position: relative;
    background: linear-gradient(
      90deg,
      #c2e2fd 20%,
      #87f2f7 40%,
      #86c6ff 60%,
      transparent 80%
    );
    background-size: 200% 200%;
    animation: dash 3s linear infinite;
    border: 4px solid transparent;
  }

  /* #fbf2b4 20%,
      #ffbb80 40%,
      #ffc155 60%, */
</style>
