<script lang="ts">
  import GoalInput from "lib/GoalInput.svelte";
  import SemanticTasks from "lib/SemanticTasks.svelte";
  import ElementaryTasks from "lib/ElementaryTasks.svelte";
  import { server_address } from "constants";
  import { onMount, setContext } from "svelte";
  import type {
    tElementaryTaskDescription,
    tElementaryTaskExecution,
  } from "types";
  let session_id: string | undefined = $state(undefined);
  setContext("session_id", () => session_id);
  let semantic_tasks = $state(undefined);
  let elementary_tasks:
    | (tElementaryTaskDescription & Partial<tElementaryTaskExecution>)[]
    | undefined = $state(undefined);
  // let elementary_task_execution_plan = $state(undefined);

  /**
   * Stores the state of the dag
   * @value semantic | elementary
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
   * convert the semantic tasks to elementary tasks
   */
  function handleConvert() {
    if (show_dag === "semantic") {
      show_dag = "elementary";
    }
    fetch(
      `${server_address}/semantic_task/decomposition_to_elementary_tasks/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ task: {}, current_steps: semantic_tasks }),
      }
    )
      .then((response) => response.json())
      .then((data) => {
        elementary_tasks = data;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  onMount(() => {
    init();
  });
</script>

<main class="w-[100vw] h-[100vh] flex flex-col py-2 px-[1rem] overflow-auto">
  {#if !session_id}
    <div class="self-center">Loading...</div>
  {/if}
  <div class="self-center max-w-[30vw] min-w-[10rem]">
    <GoalInput semantic_tasks_fetched={(data) => (semantic_tasks = data)} />
  </div>
  <div
    class="self-end py-1 px-2 bg-gray-100 min-w-[10rem] flex justify-center mt-2 rounded outline outline-gray-200"
    tabindex="0"
    role="button"
    onclick={() => handleConvert()}
    onkeyup={() => {}}
  >
    Convert
  </div>
  <div
    class="self-end py-1 px-2 bg-gray-100 min-w-[10rem] flex justify-center mt-2 rounded outline outline-gray-200"
    tabindex="0"
    role="button"
    onclick={() =>
      (show_dag = show_dag === "semantic" ? "elementary" : "semantic")}
    onkeyup={() => {}}
  >
    Switch
  </div>
  {#if show_dag === "semantic"}
    <SemanticTasks semantic_tasks={semantic_tasks || []}></SemanticTasks>
  {:else if show_dag === "elementary"}
    <ElementaryTasks elementary_tasks={elementary_tasks || []}
    ></ElementaryTasks>
  {/if}
</main>

<style lang="postcss">
</style>
