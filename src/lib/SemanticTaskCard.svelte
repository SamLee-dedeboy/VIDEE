<script lang="ts">
  import type { tSemanticTask } from "types";
  import { slide, scale } from "svelte/transition";
  let {
    task,
    id_key,
    show_explanation = $bindable(false),
    expand,
    handleDecompose = () => {},
    handleToggleExplain = () => {},
    handleToggleExpand = () => {},
    handleToggleShowSubTasks = () => {},
    handleDeleteSubTasks = () => {},
    handleDeleteTask = () => {},
  }: {
    task: tSemanticTask;
    id_key: string;
    show_explanation: boolean;
    expand: boolean;
    handleDecompose?: Function;
    handleToggleExplain?: Function;
    handleToggleExpand?: Function;
    handleToggleShowSubTasks?: Function;
    handleDeleteSubTasks?: Function;
    handleDeleteTask?: Function;
  } = $props();
  let show_subtasks = $state(false);
  let show_actions = $state(false);
  function showSubTasks() {
    show_subtasks = !show_subtasks;
    handleToggleShowSubTasks(task[id_key]);
  }
</script>

<div class="container flex flex-col w-min rounded-sm">
  <!-- <button
    class="action-button-trigger flex p-0.5 hover:bg-orange-400"
    onclick={() => (show_actions = !show_actions)}
  >
    <img
      src="ellipsis_vertical.svg"
      class="mt-0.5 w-5 h-6 pointer-events-none"
      alt="handle"
    />
  </button> -->
  <div
    class="task-card text-slate-600 w-min min-w-[18rem] pb-1 transition-all outline-2 outline-[#FFCFB1] bg-[#fbfaec] shadow rounded relative flex gap-y-1 gap-x-2"
  >
    <div class="flex flex-col grow px-2 gap-y-2">
      <div class="text-[1.3rem] font-mono text-orange-900 flex items-center">
        <span class="card-label mr-2 capitalize">{task.label}</span>
        <button
          class="shrink-0 ml-auto cursor-pointer hover:bg-orange-300 p-0.5 rounded"
          onclick={() => handleToggleExpand(task[id_key])}
          ><img src="panel_top_open.svg" alt="more" class="w-6 h-6" /></button
        >
      </div>
      {#if expand}
        <div
          in:slide
          class="border-t border-gray-300 flex flex-col min-w-[15rem]"
        >
          <div class="text-sm text-gray-400 italic">Description</div>
          {task.description}
        </div>
        <div in:slide class=" border-gray-300 flex gap-x-2 min-w-[15rem]">
          <div class="text-sm text-gray-400 italic">Confidence</div>
          <div class="text-sm">
            {task.confidence?.toFixed(2)}
          </div>
        </div>
        <div in:slide class=" border-gray-300 flex gap-x-2 min-w-[15rem]">
          <div class="text-sm text-gray-400 italic">Complexity</div>
          <div class="text-sm">
            {task.complexity?.toFixed(2)}
          </div>
        </div>
        <div class="flex gap-x-2 mt-1">
          <div class="flex justify-between flex-wrap">
            <button
              class="action-button outline-gray-200 bg-gray-100 hover:bg-green-100"
              class:disabled={task.sub_tasks === undefined ||
                task.sub_tasks.length === 0}
              class:active={show_subtasks}
              onclick={() => showSubTasks()}>SubTasks</button
            >
          </div>
        </div>
        <div in:slide class="more-actions flex flex-wrap">
          <div class="flex gap-x-2">
            <button
              class="action-button rounded outline-2 outline-orange-200 bg-orange-100 hover:bg-orange-200"
              onclick={() => handleDecompose(task)}>Decompose</button
            >
            <button
              class="action-button rounded outline-2 outline-gray-200 bg-gray-100 hover:bg-gray-200"
              >Edit</button
            >
            <button
              class="action-button rounded outline-2 outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              onclick={() => handleDeleteTask(task)}
            >
              Delete
            </button>
            <button
              class="action-button rounded outline-2 outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              tabindex="0"
              onclick={() => handleDeleteSubTasks(task)}
            >
              Delete SubTasks
            </button>
          </div>
        </div>
      {/if}
    </div>
    {#if expand}
      <div class="flex bg-[#fbfaec] border-y border-r border-gray-200">
        <div in:slide class="mt-1 flex flex-col">
          <img
            src="bot.svg"
            alt="bot"
            class="mx-2 w-7 h-7 inline-block p-0.5 border-r border-b border-gray-300 shadow min-w-[15rem] bg-gray-50"
          />
          <div class="text-sm text-gray-400 italic mx-2">Explanation</div>
          <span class="mx-2 overflow-auto">
            {task.explanation}
          </span>
        </div>
      </div>
    {/if}
  </div>
  {#if !expand}
    <div
      in:slide
      class="more-actions hidden flex-wrap absolute top-[calc(100%+1px)] left-1/2 -translate-x-1/2"
    >
      <div class="flex gap-x-0">
        <button
          class="action-button border-y-2 border-l-2 border-r-1 border-orange-200 bg-orange-100 hover:bg-orange-200"
          onclick={() => handleDecompose(task)}>Decompose</button
        >
        <button
          class="action-button border-y-2 border-x-1 border-gray-200 bg-gray-100 hover:bg-gray-200"
          >Edit</button
        >
        <button
          class="action-button border-y-2 border-x-1 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
          onclick={() => handleDeleteTask(task)}
        >
          Delete
        </button>
        <button
          class="action-button border-y-2 border-l-1 border-r-2 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
          tabindex="0"
          onclick={() => handleDeleteSubTasks(task)}
        >
          Delete SubTasks
        </button>
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "../app.css";
  .container:hover > .more-actions {
    @apply flex flex-wrap;
  }
  .action-button {
    @apply px-1 py-0.5 text-sm font-mono;
  }
  .showing-actions {
    @apply bg-green-300 outline-gray-500;
  }
  .disabled {
    @apply cursor-not-allowed bg-gray-300 outline-gray-200 opacity-50;
  }
  .active {
    @apply outline-gray-600 bg-green-200;
  }
  .task-card {
    transition:
      width 0.3s ease,
      height 0.3s ease;
  }
  .task-card:hover {
    & .close-button {
      @apply block;
    }
  }
</style>
