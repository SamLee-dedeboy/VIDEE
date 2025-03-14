<script lang="ts">
  import type { tPrimitiveTask } from "types";
  import { slide } from "svelte/transition";
  import { custom_confirm } from "lib/customConfirm";
  let {
    task,
    task_options,
    expand,
    executable,
    compiling,
    handleAddParent = () => {},
    handleExecute = () => {},
    handleInspectTask = () => {},
    handleDeleteTask = () => {},
    handleToggleExpand = () => {},
  }: {
    task: tPrimitiveTask;
    task_options: [string, string][];
    expand: boolean;
    executable: boolean;
    compiling: boolean;
    handleAddParent: Function;
    handleExecute: (task: tPrimitiveTask) => void;
    handleInspectTask: Function;
    handleDeleteTask?: Function;
    handleToggleExpand?: Function;
  } = $props();
  let adding_parent = $state(false);
</script>

<div
  class="container task-card text-slate-600 w-min min-w-[18rem] pb-1 transition-all outline-2 outline-blue-100 bg-[#F2F8FD] shadow rounded relative flex gap-y-1 gap-x-2"
>
  {#if compiling}
    <div class="absolute bottom-[calc(100%+3px)] left-0 flex items-end gap-x-1">
      <img
        src="loader_circle.svg"
        alt="loading"
        class="w-6 h-6 animate-spin opacity-80"
      />
      <span class="text-sm animate-pulse italic text-gray-500">
        compiling...
      </span>
    </div>
  {/if}
  <div class="flex flex-col grow px-2 gap-y-2">
    <div
      class="border-b border-gray-300 text-[1.2rem] italic flex items-center"
      style={`border-bottom: ${expand ? "1px solid lightgray" : "unset"}`}
    >
      <span class="card-label mr-2 capitalize">{task.label}</span>
      <button
        class="shrink-0 ml-auto cursor-pointer hover:bg-blue-300 p-0.5 rounded"
        title="Expand/Hide"
        onclick={() => handleToggleExpand(task.id)}
        ><img
          src="panel_top_open_blue.svg"
          alt="more"
          class="w-6 h-6"
        /></button
      >
    </div>
    {#if expand}
      <div
        in:slide
        class="border-b border-gray-300 flex flex-col min-w-[15rem]"
      >
        <div class="text-sm text-gray-400 italic">Description</div>
        {task.description}
      </div>
      <div class="flex flex-col justify-between gap-y-2 mt-1">
        <div class="flex gap-x-2">
          <button
            class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
            class:disabled={!executable}
            onclick={() => handleExecute(task)}>Execute</button
          >
          <button
            class="action-button outline-gray-200 bg-blue-200 hover:bg-blue-300"
            onclick={() => handleInspectTask(task)}>Inspect</button
          >
          <div class="relative">
            <button
              class="action-button outline-gray-200 bg-blue-200 hover:bg-blue-300 relative"
              onclick={() => (adding_parent = true)}
            >
              Add Parent
            </button>
            <div
              class="absolute hidden top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
            >
              <div class="flex flex-col w-max">
                {#each task_options as option}
                  <button
                    class="text-sm bg-gray-50 outline-2 outline-gray-200 px-1 py-0.5 hover:bg-gray-200"
                    onclick={() => {
                      handleAddParent(option[0]);
                      adding_parent = false;
                    }}
                  >
                    {option[1]}
                  </button>
                {/each}
              </div>
            </div>
          </div>
          <button
            class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
            onclick={async () => {
              const result = await custom_confirm(
                `Are you sure you want to delete ${task.label}?`
              );
              if (result) handleDeleteTask(task);
            }}
          >
            Delete
          </button>
        </div>
      </div>
    {/if}
  </div>
  {#if expand}
    <div
      class="flex absolute left-[100.7%] top-0 bottom-1 bg-white border-y border-r border-gray-200"
    >
      <div in:slide class="relative mt-1 flex flex-col">
        <img
          src="bot.svg"
          alt="bot"
          class="mx-2 w-7 h-7 inline-block p-0.5 border-r border-b border-gray-300 shadow min-w-[15rem]"
        />
        <div class="text-sm text-gray-400 italic mx-2">Explanation</div>
        <span class="mx-2 overflow-auto">
          {task.explanation}
        </span>
      </div>
    </div>
  {/if}
  {#if !expand}
    <div
      in:slide
      class="more-actions hidden absolute top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
    >
      <div class="flex gap-x-2">
        <button
          class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
          class:disabled={!executable}
          onclick={() => handleExecute(task)}>Execute</button
        >
        <button
          class="action-button outline-gray-200 bg-blue-200 hover:bg-blue-300"
          onclick={() => handleInspectTask(task)}>Inspect</button
        >
        <div class="relative add-parent-container">
          <button
            class="action-button outline-gray-200 bg-blue-200 hover:bg-blue-300 relative"
            onclick={() => (adding_parent = true)}
          >
            Add Parent
          </button>
          <div
            class="options absolute hidden top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
          >
            <div class="flex flex-col w-max">
              {#each task_options as option}
                <button
                  class="text-sm bg-gray-50 outline-2 outline-gray-200 px-1 py-0.5 hover:bg-gray-200"
                  onclick={() => {
                    handleAddParent(option[0]);
                    adding_parent = false;
                  }}
                >
                  {option[1]}
                </button>
              {/each}
            </div>
          </div>
        </div>
        <button
          class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
          onclick={async () => {
            const result = await custom_confirm(
              `Are you sure you want to delete ${task.label}?`
            );
            if (result) handleDeleteTask(task);
          }}
        >
          Delete
        </button>
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .container:hover > .more-actions {
    @apply flex flex-wrap;
  }
  .action-button {
    @apply outline-2 rounded px-1 py-0.5 text-sm font-mono;
  }
  .disabled {
    @apply cursor-not-allowed pointer-events-none bg-gray-300 outline-gray-200 opacity-50;
  }

  .task-card {
    transition:
      width 0.3s ease,
      height 0.3s ease;
  }
  .add-parent-container:hover .options {
    @apply block;
  }
</style>
