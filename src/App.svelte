<script lang="ts">
  import GoalInput from "lib/GoalInput.svelte";
  import SemanticTasks from "lib/SemanticTasks.svelte";
  import ElementaryTasks from "lib/ElementaryTasks.svelte";
  import { server_address } from "constants";
  let semantic_tasks = $state(undefined);
  let elementary_tasks = $state(undefined);

  /**
   * Stores the state of the dag
   * @value semantic | elementary
   */
  let show_dag = $state("semantic");

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
</script>

<main class="w-[100vw] h-[100vh] flex flex-col py-2 px-[1rem] overflow-auto">
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
