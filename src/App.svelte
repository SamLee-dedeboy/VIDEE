<script lang="ts">
  import GoalConversation from "lib/GoalConversation.svelte";
  import SemanticTasks from "lib/SemanticTasks.svelte";
  import PrimitiveTasks from "lib/PrimitiveTasks.svelte";
  import { server_address } from "constants";
  import { onMount, setContext } from "svelte";
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
  } from "types";
  import GoalInput from "lib/GoalInput.svelte";
  import PrimitiveTaskInspection from "lib/PrimitiveTaskInspection.svelte";
  let session_id: string | undefined = $state(undefined);
  setContext("session_id", () => session_id);
  let decomposing_goal = $state(false);
  let converting = $state(false);
  let semantic_tasks = $state(undefined);
  let primitive_tasks:
    | (tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>)[]
    | undefined = $state(undefined);
  let inspected_primitive_task:
    | (tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>)
    | undefined = $state(undefined);
  // let primitive_task_execution_plan = $state(undefined);

  /**
   * Stores the state of the dag
   * @value semantic | primitive
   */
  let show_dag = $state("semantic");

  async function init() {
    await fetchTest();
    await createSession();
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
  function handleDecomposeGoal(goal: string) {
    decomposing_goal = true;
    fetch(`${server_address}/goal_decomposition/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ goal, session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log({ data });
        semantic_tasks = data;
        decomposing_goal = false;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

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

  onMount(() => {
    init();
  });
</script>

<main class="w-[100vw] h-[100vh] flex py-2 px-[1rem] gap-y-1">
  {#if !session_id}
    <div class="self-center">Loading...</div>
  {:else}
    <div class="flex flex-[2_2_0%] flex-col gap-y-2">
      <div class="bg-white">
        <GoalInput {handleDecomposeGoal} />
      </div>
      <div class="flex flex-[2_2_0%] gap-x-2">
        <div class="relative grow px-2 py-1 rounded">
          <div
            class="absolute top-0 left-0 right-0 bottom-0 flex overflow-hidden"
          >
            {#if show_dag === "semantic"}
              <SemanticTasks
                {decomposing_goal}
                semantic_tasks={semantic_tasks || []}
                {handleConvert}
              ></SemanticTasks>
            {:else if show_dag === "primitive"}
              <PrimitiveTasks
                primitive_tasks={primitive_tasks || []}
                {converting}
                handleInspectPrimitiveTask={(task) =>
                  (inspected_primitive_task = task)}
              ></PrimitiveTasks>
            {/if}
          </div>
          <div
            class="absolute top-0.5 right-0.5 py-1 px-2 bg-gray-100 min-w-[10rem] flex justify-center rounded outline outline-gray-200 z-20"
            class:disabled={primitive_tasks === undefined}
            tabindex="0"
            role="button"
            onclick={() =>
              (show_dag = show_dag === "semantic" ? "primitive" : "semantic")}
            onkeyup={() => {}}
          >
            Switch
          </div>
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
      <div class="flex-1 px-2 py-1 shrink-0">Observation Panel</div>
    {:else if show_dag == "primitive"}
      <div class="flex-1 shrink-0">
        <PrimitiveTaskInspection task={inspected_primitive_task}
        ></PrimitiveTaskInspection>
      </div>
    {/if}
  {/if}
</main>

<style lang="postcss">
  .disabled {
    @apply opacity-50 pointer-events-none;
  }
</style>
