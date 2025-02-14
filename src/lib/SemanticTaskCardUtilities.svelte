<script lang="ts">
  import type { tSemanticTask } from "types";

  let {
    task,
    handleSetAsNextExpansion = () => {},
    handleDecompose = () => {},
    handleDeleteTask = () => {},
    handleDeleteSubTasks = () => {},
  }: {
    task: tSemanticTask;
    handleSetAsNextExpansion: Function;
    handleDecompose: Function;
    handleDeleteTask: Function;
    handleDeleteSubTasks: Function;
  } = $props();
</script>

<div class="flex gap-x-1 bg-white">
  <button
    class="action-button border-y-2 border-l-2 border-r-2 border-dashed border-orange-500 bg-[#fbfaec] hover:bg-orange-200 ml-auto right-0"
    tabindex="0"
    onclick={() => handleSetAsNextExpansion(task)}
  >
    Next Expansion
  </button>
  <!-- <button
    class="action-button border-y-2 border-l-2 border-r-1 border-orange-200 bg-orange-100 hover:bg-orange-200"
    onclick={() => handleDecompose(task)}>Decompose</button
  > -->
  <button
    class="action-button border-y-2 border-x-1 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
    onclick={() => handleDeleteTask(task)}
  >
    Delete
  </button>
  <button
    class="action-button border-y-2 border-l-1 border-r-2 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
    class:disabled={task.sub_tasks === undefined || task.sub_tasks.length === 0}
    tabindex="0"
    onclick={() => handleDeleteSubTasks(task)}
  >
    Delete SubTasks
  </button>
</div>

<style lang="postcss">
  @reference "../app.css";

  .action-button {
    @apply px-1 py-0.5 text-sm font-mono;
  }
  .disabled {
    @apply cursor-not-allowed pointer-events-none  outline-gray-200 opacity-50;
  }
  .active {
    @apply outline-gray-600 bg-green-200;
  }
</style>
