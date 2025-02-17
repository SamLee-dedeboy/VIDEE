<script lang="ts">
  import GoalConversation from "lib/GoalConversation.svelte";
  import SemanticTasks from "lib/SemanticTasks.svelte";
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
  import SemanticTaskInspection from "lib/SemanticTaskInspection.svelte";
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
  let max_value_path: [string[], number] = $state([[], 0]);
  let few_shot_examples_semantic_tasks = $derived.by(() => {
    const evaluations = ["complexity", "coherence", "importance"];
    const examples: Record<string, any> = {};
    semantic_tasks.forEach((task) => {
      evaluations.forEach((evaluation) => {
        if (
          task.user_evaluation[evaluation] !== task.llm_evaluation[evaluation]
        ) {
          if (!examples[evaluation]) examples[evaluation] = [];
          examples[evaluation].push({
            node: task,
            parent_node: semantic_tasks.find(
              (t) => t["MCT_id"] === task["MCT_parent_id"]
            ),
            user_evaluation: task.user_evaluation[evaluation],
            llm_evaluation: task.llm_evaluation[evaluation],
          });
        }
      });
    });
    console.log({ examples });
    return examples;
  });
  let primitive_tasks:
    | (tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>)[]
    | undefined = $state(undefined);
  let inspected_primitive_task:
    | (tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>)
    | undefined = $state(undefined);

  // let primitive_task_execution_plan = $state(undefined);
  // let goal_candidate_steps = $state([]);

  /**
   * Stores the state of the dag
   * @value semantic | primitive
   */
  let show_dag = $state("semantic");

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

  async function handleDecomposeGoalStepped_MCTS(goal: string) {
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
            max_value_path = obj["max_value_path"];
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
    if (show_dag === "semantic") {
      show_dag = "primitive";
    }
    fetch(`${server_address}/semantic_task/decomposition_to_primitive_tasks/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ task: {}, current_steps: semantic_tasks }),
    })
      .then((response) => response.json())
      .then((data) => {
        primitive_tasks = data;
        converting = false;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function handleUserFeedback(
    task_id: string,
    evaluation: string,
    value: boolean
  ) {
    const target_task_index = semantic_tasks
      .map((t) => t["MCT_id"])
      .indexOf(task_id);
    if (target_task_index !== -1) {
      semantic_tasks[target_task_index].user_evaluation[evaluation] = value;
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
    <div class="flex flex-[2_2_0%] shrink-0 flex-col gap-y-2">
      <div class="bg-white flex gap-x-2">
        <GoalInput
          handleDecomposeGoal={handleDecomposeGoalStepped_MCTS}
          bind:mode
          {streaming_states}
        />
        <button
          id="stop"
          class="outline-2 outline-red-300 p-2 bg-red-100 rounded hover:bg-red-200"
          class:disabled={!(
            streaming_states.started && !streaming_states.paused
          )}
          onclick={() => {
            if (stream_controller !== undefined) {
              stream_controller.abort(); // Stop streaming
              stream_controller = undefined;
            }
          }}>Stop Streaming</button
        >
      </div>
      <div class="flex flex-[2_2_0%] gap-x-2">
        <div
          class="relative grow px-2 py-1"
          class:loading-canvas={streaming_states.started &&
            !streaming_states.paused}
        >
          <div
            class="absolute top-0 left-0 right-0 bottom-0 flex overflow-hidden"
          >
            {#if show_dag === "semantic"}
              <SemanticTasksTree
                {decomposing_goal}
                {semantic_tasks}
                {streaming_states}
                bind:next_expansion
                {max_value_path}
                {handleConvert}
              ></SemanticTasksTree>
              <!-- <SemanticTasks
                {decomposing_goal}
                semantic_tasks={semantic_tasks || []}
                {handleConvert}
              ></SemanticTasks> -->
            {:else if show_dag === "primitive"}
              <PrimitiveTasks
                primitive_tasks={primitive_tasks || []}
                {converting}
                handleInspectPrimitiveTask={(task) =>
                  (inspected_primitive_task = task)}
              ></PrimitiveTasks>
            {/if}
          </div>
          <button
            class="absolute top-0.5 left-0.5 py-1 px-2 min-w-[10rem] flex items-center justify-center rounded outline-2 outline-gray-200 shadow-md z-20 gap-x-2 text-slate-700 italic"
            class:disabled={primitive_tasks === undefined}
            style:color={show_dag === "semantic"
              ? "oklch(0.623 0.214 259.815)"
              : "oklch(0.705 0.213 47.604)"}
            tabindex="0"
            onclick={() =>
              (show_dag = show_dag === "semantic" ? "primitive" : "semantic")}
            onkeyup={() => {}}
          >
            <div class="flex gap-x-2 items-center">
              {#if show_dag === "semantic"}
                <div class="flex items-center justify-center p-1 bg-blue-200">
                  <img
                    src="forward.svg"
                    alt="forward"
                    class="w-4 h-4 bg-blue-200"
                  />
                </div>
                Primitive Tasks
              {:else if show_dag === "primitive"}
                <div class="flex items-center justify-center p-1 bg-orange-200">
                  <img src="backward.svg" alt="back" class="w-4 h-4" />
                </div>
                Semantic Tasks
              {/if}
            </div>
          </button>
        </div>
        <!-- <div class="max-w-[30vw] min-w-[10rem] flex">
          <GoalConversation
            {handleDecomposeGoal}
            semantic_tasks={semantic_tasks || []}
          />
        </div> -->
      </div>
    </div>
    {#if show_dag == "semantic"}
      <div class="flex-1">
        <SemanticTaskInspection
          few_shot_examples={few_shot_examples_semantic_tasks}
        ></SemanticTaskInspection>
      </div>
    {:else if show_dag == "primitive"}
      <div class="flex-1 overflow-auto">
        <PrimitiveTaskInspection task={inspected_primitive_task}
        ></PrimitiveTaskInspection>
      </div>
    {/if}
  {/if}
</main>

<style lang="postcss">
  .disabled {
    /* @apply opacity-50 pointer-events-none; */
    @apply invisible pointer-events-none;
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
