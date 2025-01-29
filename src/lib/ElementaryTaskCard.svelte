<script lang="ts">
  import type {
    tElementaryTaskDescription,
    tElementaryTaskExecution,
  } from "types";
  import { slide } from "svelte/transition";
  let {
    task,
    executable,
    handleExecute,
  }: {
    task: tElementaryTaskDescription & Partial<tElementaryTaskExecution>;
    executable: boolean;
    handleExecute: (
      task: tElementaryTaskDescription & tElementaryTaskExecution
    ) => void;
  } = $props();
  let expand = $state(false);
  let show_actions = $state(false);
  $inspect(task);
</script>

<div
  class="task-card text-slate-600 w-min min-w-[16rem] transition-all outline outline-2 outline-blue-100 bg-[#F2F8FD] shadow px-2 py-1 rounded relative flex gap-y-1 gap-x-2"
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
    <div in:slide class="border-b border-gray-300 flex flex-col min-w-[15rem]">
      <div class="text-sm text-gray-400 italic">Description</div>
      {task.description}
    </div>
    <div class="flex flex-col justify-between gap-y-2 mt-1">
      <div class="flex">
        <button
          class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
          class:disabled={!executable}
          onclick={() => handleExecute(task)}>Execute</button
        >
        <div
          role="button"
          tabindex="0"
          class={`action-trigger action-button ml-auto flex justify-center outline outline-gray-200 bg-green-100 hover:bg-green-300 relative `}
          class:showing-actions={show_actions}
          onclick={() => (show_actions = !show_actions)}
          onkeyup={() => {}}
        >
          More Actions
          {#if show_actions}
            <div
              class="more-actions absolute top-[calc(100%+5px)] left-1/2 -translate-x-1/2"
            >
              <div class="flex gap-x-2">
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
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
  {#if expand}
    <div in:slide class="flex flex-col text-xs min-w-[15rem] max-w-[20rem]">
      <div class="flex text-lg justify-center">Input/Output Format</div>
      <div class="flex flex-col">
        <div class="option-label">State Input Key:</div>
        <div class="flex items-center justify-center option-value">
          {task.state_input_key}
        </div>
      </div>
      <div class="flex flex-col">
        <div class="option-label">Doc Input Keys:</div>
        {#if task.doc_input_keys}
          <div class="flex gap-x-2 items-center justify-around">
            {#each task.doc_input_keys as input_key}
              <div class="flex items-center justify-center option-value">
                {input_key}
              </div>
            {/each}
          </div>
        {/if}
      </div>
      <div class="flex flex-col">
        <div class="option-label">State Output Key:</div>
        <div class="flex items-center justify-center option-value">
          {task.state_output_key}
        </div>
      </div>
    </div>
    <div in:slide class="flex flex-col min-w-[15rem] text-xs">
      <div class="flex text-lg justify-center">Execution</div>
      <div class="flex items-center gap-x-2">
        <div class="option-label">Tool:</div>
        <div class="flex items-center justify-center option-value">
          {task.execution?.tool || "N/A"}
        </div>
      </div>
      <div class="flex flex-col">
        <div class="option-label">Parameters:</div>
        {#each Object.keys(task.execution?.parameters || {}) as key}
          <div class="flex items-center gap-x-2 gap-y-1">
            <div class="option-label min-w-[3rem]">{key}:</div>
            <div
              class="flex items-center justify-center option-value !my-0 max-w-[10rem] overflow-scroll"
            >
              {task.execution?.parameters[key]}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  .option-label {
    @apply text-sm text-gray-700 italic;
  }
  .option-value {
    @apply outline outline-1 outline-gray-300 rounded px-2 my-2 hover:bg-gray-200 transition-all cursor-pointer;
  }
  .action-button {
    @apply outline outline-2 rounded px-1 py-0.5 text-sm font-mono;
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
