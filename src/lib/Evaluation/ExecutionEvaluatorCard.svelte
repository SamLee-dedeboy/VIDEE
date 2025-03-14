<script lang="ts">
  import type { tExecutionEvaluator } from "types";
  import { slide } from "svelte/transition";
  import { primitiveTaskExecutionStates } from "../ExecutionStates.svelte";
  import { custom_confirm } from "lib/customConfirm";
  let {
    evaluator = $bindable(),
    expand,
    handleExecute = () => {},
    handleInspectEvaluator = () => {},
    handleDeleteEvaluator = () => {},
    handleToggleExpand = () => {},
  }: {
    evaluator: tExecutionEvaluator;
    expand: boolean;
    handleExecute: (task: tExecutionEvaluator) => void;
    handleInspectEvaluator: Function;
    handleDeleteEvaluator?: Function;
    handleToggleExpand?: Function;
  } = $props();
</script>

<div
  in:slide
  class="container evaluator-card text-slate-600 w-min min-w-[18rem] pb-1 transition-all outline-2 outline-emerald-100 shadow rounded relative flex gap-y-1 gap-x-2"
>
  <div class="flex flex-col grow px-2 gap-y-2">
    <div
      class="border-b border-gray-300 text-[1.2rem] italic flex items-center"
      style={`border-bottom: ${expand ? "1px solid lightgray" : "unset"}`}
    >
      <span class="card-label mr-2 capitalize">{evaluator.name}</span>
      <button
        class="shrink-0 ml-auto cursor-pointer hover:bg-emerald-200 p-0.5 rounded"
        title="Expand/Hide"
        onclick={() => handleToggleExpand(evaluator.name)}
        ><img
          src="panel_top_open_emerald.svg"
          alt="more"
          class="w-6 h-6"
        /></button
      >
    </div>

    {#if expand}
      <div
        in:slide
        class="border-b border-gray-300 flex flex-col min-w-[18rem]"
      >
        <div class="text-sm text-gray-400 italic">Definition</div>
        {evaluator.definition}
        <button
          class="delete-button hidden absolute top-1/2 -translate-y-1/2 left-0 opacity-60 hover:opacity-100"
          onclick={async () => {
            const result = await custom_confirm(
              `Are you sure you want to delete ${evaluator.name}?`
            );
            if (result) handleDeleteEvaluator(evaluator);
          }}
        >
          <img src="trash.svg" alt="delete" class="w-4 h-4" />
        </button>
      </div>
      <div class="task-option-container flex gap-x-2 text-sm text-slate-700">
        <div class="text-sm text-gray-400 italic">Target:</div>
        <div class="options flex gap-2 flex-wrap text-sm">
          {evaluator.task}
        </div>
      </div>
      <div class="flex flex-col justify-between gap-y-2 mt-1">
        <div class="flex gap-x-2">
          <button
            class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
            class:disabled={!primitiveTaskExecutionStates.executed(
              evaluator.task
            )}
            onclick={() => handleExecute(evaluator)}>Execute</button
          >
          <button
            class="action-button outline-gray-200 bg-emerald-200 hover:bg-emerald-300"
            onclick={() => handleInspectEvaluator(evaluator)}>Inspect</button
          >
          <button
            class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
            onclick={async () => {
              const result = await custom_confirm(
                `Are you sure you want to delete ${evaluator.name}?`
              );
              if (result) handleDeleteEvaluator(evaluator);
            }}
          >
            Delete
          </button>
        </div>
      </div>
    {/if}
  </div>
  {#if !expand}
    <div
      in:slide
      class="more-actions hidden absolute top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
    >
      <div class="flex flex-col justify-between gap-y-2 mt-1">
        <div class="flex gap-x-2">
          <button
            class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
            class:disabled={!primitiveTaskExecutionStates.executed(
              evaluator.task
            )}
            onclick={() => handleExecute(evaluator)}>Execute</button
          >
          <button
            class="action-button outline-gray-200 bg-emerald-200 hover:bg-emerald-300"
            onclick={() => handleInspectEvaluator(evaluator)}>Inspect</button
          >
          <button
            class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
            onclick={() => handleDeleteEvaluator(evaluator)}
          >
            <!-- <img src="close.svg" alt="x" /> -->
            Delete
          </button>
        </div>
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
</style>
