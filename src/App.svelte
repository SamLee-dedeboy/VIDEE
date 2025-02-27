<script lang="ts">
  import GoalConversation from "lib/GoalConversation.svelte";
  import SemanticTaskPlan from "lib/SemanticTaskPlan.svelte";
  import SemanticTasksTree from "lib/SemanticTasksTree.svelte";
  import PrimitiveTasks from "lib/PrimitiveTasks.svelte";
  import { server_address } from "constants";
  import { onMount, setContext } from "svelte";
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
    tSemanticTask,
  } from "types";
  import GoalInput from "lib/GoalInput.svelte";
  import PrimitiveTaskInspection from "lib/PrimitiveTaskInspection.svelte";
  import SemanticTaskTreeInspection from "lib/SemanticTaskTreeInspection.svelte";
  import ExecutionInspection from "lib/ExecutionInspection.svelte";
  import ExecutionEvaluators from "lib/ExecutionEvaluators.svelte";
  import type { stringify } from "postcss";
  let session_id: string | undefined = $state(undefined);
  setContext("session_id", () => session_id);
  let decomposing_goal = $state(false);
  let converting = $state(false);

  // stream states
  let streaming_states = $state({
    started: false,
    paused: false,
    finished: false,
  });
  let stream_controller: any = $state(undefined);
  let mode = $state("step");

  let semantic_tasks: tSemanticTask[] = $state([]);
  let next_expansion: tSemanticTask | undefined = $state(undefined);
  let selected_semantic_task_path: tSemanticTask[] = $state([]);
  let few_shot_examples_semantic_tasks: Record<string, any> = $state({});

  let user_goal: string = $state("");
  /**
   * updates the few shot examples every time semantic tasks are updated
   */
  $effect(() => {
    const evaluations = ["complexity", "coherence", "importance"];
    console.log({ semantic_tasks });
    semantic_tasks.forEach((task) => {
      evaluations.forEach((evaluation) => {
        if (
          task.user_evaluation[evaluation] !== task.llm_evaluation[evaluation]
        ) {
          if (!few_shot_examples_semantic_tasks[evaluation])
            few_shot_examples_semantic_tasks[evaluation] = [];
          if (
            !few_shot_examples_semantic_tasks[evaluation].find(
              (t) => t.node.label === task.label
            )
          ) {
            few_shot_examples_semantic_tasks[evaluation].push({
              node: task,
              parent_node: semantic_tasks.find(
                (t) => t.MCT_id === task.MCT_parent_id
              ),
              user_evaluation: task.user_evaluation[evaluation],
              llm_evaluation: task.llm_evaluation[evaluation],
              explanation: undefined,
            });
          }
        }
      });
    });
    console.log(
      "few shot examples: ",
      $state.snapshot(few_shot_examples_semantic_tasks)
    );
  });

  function setFewShotExampleExplanation(
    task: tSemanticTask,
    evaluation: string,
    explanation: string
  ) {
    console.log({
      task,
      evaluation,
      explanation,
      few_shot_examples_semantic_tasks: $state.snapshot(
        few_shot_examples_semantic_tasks
      ),
    });
    const example_index = few_shot_examples_semantic_tasks[evaluation]
      .map((t) => t.node.MCT_id)
      .indexOf(task.MCT_id);
    console.log({ example_index });
    if (example_index !== -1) {
      few_shot_examples_semantic_tasks[evaluation][example_index].explanation =
        explanation;
    }
  }
  setContext("setFewShotExampleExplanation", setFewShotExampleExplanation);
  let primitive_tasks: (tPrimitiveTaskDescription &
    Partial<tPrimitiveTaskExecution>)[] = $state([]);
  let inspected_primitive_task:
    | (tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>)
    | undefined = $state(undefined);

  // let primitive_task_execution_plan = $state(undefined);
  // let goal_candidate_steps = $state([]);

  /**
   * Stores the state of the dag
   * @value semantic| mcts
   */
  let show_dag = $state("mcts");

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

  // async function fetchStream() {
  //   stream_controller = new AbortController();
  //   const signal = stream_controller.signal;
  //   try {
  //     const response = await fetch(`${server_address}/test/stream/`, {
  //       method: "POST",
  //       headers: {
  //         "Content-Type": "application/json",
  //       },
  //       body: JSON.stringify({
  //         session_id,
  //       }),

  //       signal,
  //     });
  //     if (!response.body) {
  //       throw new Error("Stream error");
  //     }
  //     const reader = response.body.getReader();
  //     const decoder = new TextDecoder();

  //     let buffer = "";

  //     while (true) {
  //       const { done, value } = await reader.read();
  //       if (done) break;

  //       buffer += decoder.decode(value, { stream: true });

  //       // Process complete JSON objects line by line
  //       let lines = buffer.split("\n");
  //       buffer = lines.pop() || ""; // Keep the last incomplete part for the next iteration

  //       for (let line of lines) {
  //         if (line) {
  //           const obj = JSON.parse(line);
  //           console.log("Received:", obj);
  //           // You can update UI here
  //         }
  //       }
  //     }
  //   } catch (error: any) {
  //     if (error.name === "AbortError") {
  //       streaming_states.paused = true;
  //       console.log("Stream aborted");
  //     } else {
  //       console.error("Error:", error);
  //     }
  //   } finally {
  //     stream_controller = null;
  //   }

  //   console.log("Stream finished");
  // }

  function createSession() {
    let random_session_id = Math.random().toString(36).substring(2, 15);
    fetch(`${server_address}/session/create/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id: random_session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        session_id = data.session_id;
        console.log("Session created:", session_id);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
  /**
   * Decompose the goal into semantic tasks
   */
  // function handleDecomposeGoal(goal: string) {
  //   decomposing_goal = true;
  //   fetch(`${server_address}/goal_decomposition/`, {
  //     method: "POST",
  //     headers: {
  //       "Content-Type": "application/json",
  //     },
  //     body: JSON.stringify({ goal, session_id }),
  //   })
  //     .then((response) => response.json())
  //     .then((data) => {
  //       console.log({ data });
  //       semantic_tasks = data;
  //       decomposing_goal = false;
  //     })
  //     .catch((error) => {
  //       console.error("Error:", error);
  //     });
  // }
  async function dev_handleDecomposeGoalStepped_MCTS(goal: string) {
    fetch(`${server_address}/dev/semantic_task/plan`)
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
    dev_handleDecomposeGoalStepped_MCTS(goal);
    return;
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
      });
  }

  // async function handleDecomposeGoalStepped_BeamSearch(goal: string) {
  //   streaming_states.started = true;
  //   streaming_states.paused = false;
  //   stream_controller = new AbortController();
  //   const signal = stream_controller.signal;
  //   try {
  //     const response = await fetch(
  //       `${server_address}/goal_decomposition/beam_search/stepped/`,
  //       {
  //         method: "POST",
  //         headers: {
  //           "Content-Type": "application/json",
  //         },
  //         body: JSON.stringify({
  //           goal,
  //           session_id,
  //           user_steps:
  //             semantic_tasks === undefined ? [] : [[semantic_tasks, 5]],
  //         }),
  //         signal,
  //       }
  //     );
  //     if (!response.body) {
  //       throw new Error("Stream error");
  //     }
  //     const reader = response.body.getReader();
  //     const decoder = new TextDecoder();

  //     let buffer = "";

  //     while (true) {
  //       const { done, value } = await reader.read();
  //       if (done) break;

  //       buffer += decoder.decode(value, { stream: true });

  //       // Process complete JSON objects line by line
  //       let lines = buffer.split("\n");
  //       buffer = lines.pop() || ""; // Keep the last incomplete part for the next iteration

  //       for (let line of lines) {
  //         if (line) {
  //           const obj = JSON.parse(line);
  //           console.log("Received:", obj);
  //           semantic_tasks = obj["semantic_tasks"][0][0];
  //         }
  //       }
  //     }
  //     console.log("Stream finished");
  //     streaming_states.started = false;
  //     streaming_states.paused = false;
  //     streaming_states.finished = true;
  //   } catch (error: any) {
  //     if (error.name === "AbortError") {
  //       streaming_states.paused = true;
  //       console.log("Stream aborted");
  //     } else {
  //       console.error("Error:", error);
  //     }
  //   } finally {
  //     stream_controller = undefined;
  //   }
  // }

  /**
   * convert the semantic tasks to primitive tasks
   */

  function handleConvert() {
    converting = true;
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
        primitive_tasks = data;
        converting = false;
        if (show_dag === "semantic") {
          show_dag = "primitive";
        }
      });
  }
  // stream convert
  // async function _handleConvert() {
  //   converting = true;
  //   if (show_dag === "semantic") {
  //     show_dag = "primitive";
  //   }
  //   streaming_states.started = true;
  //   streaming_states.paused = false;
  //   stream_controller = new AbortController();
  //   const signal = stream_controller.signal;
  //   console.log({ selected_semantic_task_path });
  //   try {
  //     const response = await fetch(
  //       `${server_address}/semantic_task/decomposition_to_primitive_tasks/`,
  //       {
  //         method: "POST",
  //         headers: {
  //           "Content-Type": "application/json",
  //         },
  //         body: JSON.stringify(
  //           { semantic_tasks: selected_semantic_task_path },
  //           signal
  //         ),
  //       }
  //     );
  //     if (!response.body) {
  //       throw new Error("Stream error");
  //     }

  //     const reader = response.body.getReader();
  //     const decoder = new TextDecoder();

  //     let buffer = "";

  //     while (true) {
  //       const { done, value } = await reader.read();
  //       if (done) break;

  //       buffer += decoder.decode(value, { stream: true });

  //       // Process complete JSON objects line by line
  //       let lines = buffer.split("\n");
  //       buffer = lines.pop() || ""; // Keep the last incomplete part for the next iteration

  //       for (let line of lines) {
  //         if (line) {
  //           const obj = JSON.parse(line);
  //           console.log("Received:", obj);
  //           if (!primitive_tasks) primitive_tasks = [];
  //           primitive_tasks = primitive_tasks.concat(
  //             obj["primitive_tasks"] as any[]
  //           );
  //           const semantic_task = obj["semantic_task"]; // the semantic task that was converted

  //           if (mode === "step" && stream_controller !== undefined) {
  //             stream_controller.abort(); // Stop streaming
  //             stream_controller = undefined;
  //           }
  //         }
  //       }
  //     }
  //     console.log("Stream finished");
  //     streaming_states.started = false;
  //     streaming_states.paused = false;
  //     streaming_states.finished = true;
  //     converting = false;
  //   } catch (error: any) {
  //     if (error.name === "AbortError") {
  //       streaming_states.paused = true;
  //       console.log("Stream aborted");
  //     } else {
  //       console.error("Error:", error);
  //     }
  //   } finally {
  //     stream_controller = undefined;
  //   }
  // }

  function handleUserFeedback(
    task_id: string,
    evaluation: string,
    value: boolean
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
        3;

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
  }
  setContext("handleUserFeedback", handleUserFeedback);

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
            class="min-w-[6rem] px-2 py-1 font-mono text-slate-700 outline-1 outline-gray-400 hover:outline-orange-200 hover:outline-2 hover: z-10 hover:!text-slate-700"
            class:disabled={streaming_states.started &&
              !streaming_states.paused}
            style={`${show_dag === "semantic" ? "background-color: oklch(0.954 0.038 75.164); opacity: 1;" : "background-color: #fafafa; color: rgba(0, 0, 0, 0.2) "}`}
            onclick={() => (show_dag = "semantic")}>Plan</button
          >
          <button
            class="min-w-[6rem] px-2 py-1 font-mono rounded-r outline-1 outline-gray-400 text-slate-700 hover:outline-blue-300 hover:outline-2 hover:z-10 hover:!text-slate-700"
            class:disabled={primitive_tasks.length === 0 ||
              (streaming_states.started && !streaming_states.paused)}
            style={`${show_dag === "primitive" ? "background-color: oklch(0.882 0.059 254.128); opacity: 1;" : "background-color: #fafafa;  color: rgba(0, 0, 0, 0.2)"}`}
            onclick={() => (show_dag = "primitive")}>Execution</button
          >
        </div>
      </div>
      <div class="flex flex-[2_2_0%] gap-x-2">
        <div
          class="relative grow px-2 py-1"
          class:loading-canvas={converting ||
            (streaming_states.started && !streaming_states.paused)}
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
            {:else if show_dag == "semantic"}
              <SemanticTaskPlan
                {decomposing_goal}
                semantic_tasks={selected_semantic_task_path || []}
                {handleConvert}
                {primitive_tasks}
                {converting}
                handleInspectPrimitiveTask={(task) => {
                  console.log("inspecting task", task);
                  inspected_primitive_task = task;
                }}
              ></Execution>
              <!-- <SemanticTaskPlan
                {decomposing_goal}
                semantic_tasks={selected_semantic_task_path || []}
                {handleConvert}
              ></SemanticTaskPlan> -->
              <!-- {:else if show_dag === "primitive"}
              <PrimitiveTasks
                {primitive_tasks}
                {converting}
                handleInspectPrimitiveTask={(task) =>
                  (inspected_primitive_task = task)}
              ></PrimitiveTasks>
            {/if}
          </div>
        </div>
      </div>
    </div>
    <div class="flex-1 flex flex-col overflow-auto gap-y-2">
      {#if show_dag === "mcts"}
        <SemanticTaskTreeInspection
          few_shot_examples={few_shot_examples_semantic_tasks}
        ></SemanticTaskTreeInspection>
      {:else if show_dag === "semantic"}
        <ExecutionInspection
          semantic_tasks={selected_semantic_task_path}
          primitive_task={inspected_primitive_task}
        ></ExecutionInspection>
        <!-- {:else if show_dag === "primitive"}
        <PrimitiveTaskInspection
          task={inspected_primitive_task || {}}
          {primitive_tasks}
        ></PrimitiveTaskInspection> -->
      {/if}
    </div>
  {/if}
</main>

<style lang="postcss">
  .disabled {
    @apply !opacity-50 pointer-events-none;
  }
  .hidden {
    @apply hidden;
  }

  /* #fbf2b4 20%,
      #ffbb80 40%,
      #ffc155 60%, */
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

  @keyframes dash {
    0% {
      background-position: 0% 0%;
    }
    100% {
      background-position: 200% 150%;
    }
  }
  @keyframes ripple {
    0% {
      background-size: 0% 0%;
      opacity: 1;
    }
    100% {
      background-size: 100% 100%;
      opacity: 0;
    }
  }
</style>
