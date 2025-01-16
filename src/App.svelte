<script lang="ts">
  import GoalInput from "lib/GoalInput.svelte";
  import SemanticTasks from "lib/SemanticTasks.svelte";
  let semantic_tasks = $state(undefined);
</script>

<main class="w-[100vw] h-[100vh] flex flex-col py-2 px-[1rem] overflow-auto">
  <div class="self-center max-w-[30vw] min-w-[10rem]">
    <GoalInput semantic_tasks_fetched={(data) => (semantic_tasks = data)} />
  </div>
  <SemanticTasks {semantic_tasks}></SemanticTasks>
</main>

<style lang="postcss">
</style>
