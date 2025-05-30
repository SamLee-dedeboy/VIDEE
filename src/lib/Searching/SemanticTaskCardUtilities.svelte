<script lang="ts">
  import type { tSemanticTask } from "types";
  import { custom_confirm } from "lib/customConfirm";

  let {
    task,
    handleSetAsNextExpansion = () => {},
    handleRegenerate = () => {},
    handleDecompose = () => {},
    handleDeleteTask = () => {},
    handleDeleteSubTasks = () => {},
    handleSelectPath = () => {},
    handleAddChild = () => {},
    handleToggleChildren = () => {},
  }: {
    task: tSemanticTask;
    handleSetAsNextExpansion: Function;
    handleDecompose: Function;
    handleRegenerate: Function;
    handleDeleteTask: Function;
    handleDeleteSubTasks: Function;
    handleSelectPath: Function;
    handleAddChild: Function;
    handleToggleChildren: Function;
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
    class="action-button border-y-2 border-x-1 border-blue-300 bg-blue-100 hover:bg-blue-200 ml-auto right-0"
    onclick={() => handleRegenerate(task)}
  >
    Try Again
  </button>
  <div class="relative children-container">
    <div
      class="action-button flex items-center select-none border-y-2 border-x-1 border-orange-300 bg-orange-100 h-full"
    >
      Children
    </div>
    <div
      class="options-children w-full font-mono text-xs hidden absolute flex-col gap-y-0 top-[calc(100%+0px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
    >
      <!-- <button
        class="bg-orange-50 outline-2 w-max outline-orange-200 hover:bg-orange-200 text-sm px-1 py-0.5"
        onclick={() => handleToggleChildren()}>Show/Hide</button
      > -->
      <button
        class="bg-orange-50 outline-2 outline-orange-200 hover:bg-orange-200 text-sm px-1 py-0.5"
        onclick={() => handleAddChild(task)}>Add</button
      >
    </div>
  </div>
  <button
    class="action-button border-y-2 border-x-1 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
    onclick={async () => {
      const result = await custom_confirm(
        `Are you sure you want to delete ${task.label}?`
      );
      if (result) handleDeleteTask(task);
    }}
  >
    Delete
  </button>
  <!-- <button
    class="action-button border-y-2 border-l-1 border-r-2 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
    class:disabled={task.sub_tasks === undefined || task.sub_tasks.length === 0}
    tabindex="0"
    onclick={() => handleDeleteSubTasks(task)}
  >
    Delete SubTasks
  </button> -->
  <button
    class="action-button border-2 border-black bg-[#fbfaec] hover:bg-orange-100 ml-auto right-0"
    tabindex="0"
    onclick={() => {
      console.log("Choose Path clicked", task);
      handleSelectPath(task);
    }}
  >
    Choose Path
  </button>
</div>

<style lang="postcss">
  @reference "tailwindcss";

  .action-button {
    @apply px-1 py-0.5 text-sm font-mono;
  }
  .disabled {
    @apply cursor-not-allowed pointer-events-none  outline-gray-200 opacity-50;
  }
  .active {
    @apply outline-gray-600 bg-green-200;
  }
  .children-container:hover .options-children {
    @apply !flex;
  }
</style>
