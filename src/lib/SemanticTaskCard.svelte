<script lang="ts">
  import type { tSemanticTask } from "types";
  import { slide, scale } from "svelte/transition";
  let {
    task,
    handleDecompose = () => {},
    handleToggle = () => {},
    handleDeleteChildren = () => {},
  }: {
    task: tSemanticTask;
    handleDecompose?: Function;
    handleToggle?: Function;
    handleDeleteChildren?: Function;
  } = $props();
  let expand = $state(false);
  let show_subtasks = $state(false);
  let show_actions = $state(false);
  function showSubTasks() {
    show_subtasks = !show_subtasks;
    handleToggle();
  }
</script>

<div
  class="task-card text-slate-600 w-min min-w-[18rem] transition-all outline outline-2 outline-gray-200 bg-[#fbfaec] shadow px-2 py-1 rounded relative flex gap-y-1 gap-x-2"
>
  <div class="flex flex-col grow">
    <div
      class="border-b border-gray-300 text-[1.2rem] italic flex items-center"
    >
      <span class="card-label mr-2 capitalize">{task.label}</span>
      <span
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
      </span>
    </div>
    {#if true}
      <div
        in:slide
        class="border-b border-gray-300 flex flex-col min-w-[15rem]"
      >
        <div class="text-sm text-gray-400 italic">Description</div>
        {task.description}
      </div>
    {/if}
    <div class="flex flex-col justify-between gap-y-2 mt-1">
      <div class="flex justify-between flex-wrap">
        <button
          class="action-button outline-gray-200 bg-gray-100 hover:bg-green-100"
          class:disabled={task.children === undefined ||
            task.children.length === 0}
          class:active={show_subtasks}
          onclick={() => showSubTasks()}>SubTasks</button
        >
      </div>
      <div class="flex flex-col gap-x-2 relative">
        <div
          role="button"
          tabindex="0"
          class={`action-trigger action-button flex justify-center outline outline-gray-200 bg-green-100 hover:bg-green-300 `}
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
                >
                  <!-- <img src="close.svg" alt="x" /> -->
                  Delete
                </button>
                <button
                  class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
                  tabindex="0"
                  onclick={() => handleDeleteChildren(task)}
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
      class="flex absolute left-[101%] top-0 bottom-1 bg-white px-2 border-y border-r border-gray-200"
    >
      <div in:slide class=" relative mt-1 mb-2">
        <img
          src="bot.svg"
          alt="bot"
          class="w-7 h-7 inline-block p-0.5 border-r border-b border-gray-300 shadow min-w-[15rem]"
        />
        <div class="text-sm text-gray-400 italic">Explanation</div>
        <span class="">
          {task.explanation}
        </span>
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  .action-button {
    @apply outline outline-2 rounded px-1 py-0.5 text-sm font-mono;
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
