<script lang="ts">
  import type { tSemanticTask } from "types";
  import { slide, scale } from "svelte/transition";
  let {
    task,
    expand = $bindable(false),
    handleDecompose = () => {},
    handleToggleExpand = () => {},
    handleToggleShowSubTasks = () => {},
    handleDeleteSubTasks = () => {},
    handleDeleteTask = () => {},
  }: {
    task: tSemanticTask;
    expand: boolean;
    handleDecompose?: Function;
    handleToggleExpand?: Function;
    handleToggleShowSubTasks?: Function;
    handleDeleteSubTasks?: Function;
    handleDeleteTask?: Function;
  } = $props();
  let show_subtasks = $state(false);
  let show_actions = $state(false);
  function showSubTasks() {
    show_subtasks = !show_subtasks;
    handleToggleShowSubTasks(task.id);
  }
</script>

<div
  class="task-card text-slate-600 w-min min-w-[18rem] pb-1 transition-all outline-2 outline-[#FFCFB1] bg-[#fbfaec] shadow rounded relative flex gap-y-1 gap-x-2"
>
  <div class="flex flex-col grow px-2 gap-y-2">
    <div
      class="border-b border-gray-300 text-[1.2rem] italic flex items-center"
    >
      <span class="card-label mr-2 capitalize">{task.label}</span>
      <!-- <span
        tabindex="0"
        role="button"
        class="ml-auto right-0 mb-0.5 shrink-0 w-7 p-1 self-stretch flex cursor-pointer hover:!bg-gray-200 rounded"
        style:background-color={expand ? "rgb(187 247 208)" : "unset"}
        onclick={() => {
          expand = !expand;
        }}
        onkeyup={() => {}}
      >
        {#if expand}
          <img src="panel_left_close.svg" class="" alt="collapse" />
        {:else}
          <img src="panel_left_open.svg" class="" alt="expand" />
        {/if}
      </span> -->
    </div>
    <div in:slide class=" border-gray-300 flex flex-col min-w-[15rem]">
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
      <div class="flex flex-col gap-x-2 relative grow">
        <div
          role="button"
          tabindex="0"
          class={`action-trigger action-button flex justify-center outline outline-gray-200 bg-green-100 hover:bg-green-300 cursor-pointer`}
          class:showing-actions={show_actions}
          onclick={() => (show_actions = !show_actions)}
          onkeyup={() => {}}
        >
          Actions
          {#if show_actions}
            <div
              class="more-actions absolute top-[calc(100%+5px)] left-1/2 -translate-x-1/2"
            >
              <div class="flex gap-x-2">
                <button
                  class="action-button outline-orange-200 bg-orange-100 hover:bg-orange-200"
                  onclick={() => handleDecompose(task)}>Decompose</button
                >
                <button
                  class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
                  >Edit</button
                >
                <button
                  class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
                  onclick={() => handleDeleteTask(task)}
                >
                  <!-- <img src="close.svg" alt="x" /> -->
                  Delete
                </button>
                <button
                  class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
                  tabindex="0"
                  onclick={() => handleDeleteSubTasks(task)}
                >
                  <!-- <img src="close.svg" alt="x" /> -->
                  Delete SubTasks
                </button>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
  {#if expand}
    <div
      class="flex absolute left-[100.7%] top-0 bottom-1 bg-white border-y border-r border-gray-200"
    >
      <div in:slide class="mt-1 flex flex-col">
        <img
          src="bot.svg"
          alt="bot"
          class="mx-2 w-7 h-7 inline-block p-0.5 border-r border-b border-gray-300 shadow min-w-[15rem]"
        />
        <div class="text-sm text-gray-400 italic mx-2">Explanation</div>
        <span class="mx-2 overflow-auto">
          {task.explanation}
        </span>
        <button
          class="p-0.5 bg-[#FFCFB1] mt-auto hover:bg-orange-400"
          onclick={() => handleToggleExpand(task.id)}
        >
          <img
            src="chevron_left.svg"
            class="mt-0.5 w-5 h-4 pointer-events-none"
            alt="handle"
          />
        </button>
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "../app.css";
  .action-button {
    @apply outline-2 rounded px-1 py-0.5 text-sm font-mono;
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
