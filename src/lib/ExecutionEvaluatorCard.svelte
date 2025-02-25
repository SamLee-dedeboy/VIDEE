<script lang="ts">
  import { trim } from "lib/trim";
  import type { tExecutionEvaluator } from "types";
  import { slide } from "svelte/transition";
  import PromptTemplate from "./PromptTemplate.svelte";
  let {
    evaluator = $bindable(),
    tasks,
    handleDelete,
    loading = false,
  }: {
    evaluator: tExecutionEvaluator;
    tasks: [string, string][];
    loading: boolean;
    handleDelete: Function;
  } = $props();
  let show_parameters = $state(false);

  function isEmpty(string: string | null | undefined): boolean {
    return string === undefined || string === null || string === "";
  }
  $effect(() => {
    if (evaluator.parameters) {
      show_parameters = true;
    }
  });
</script>

<div
  in:slide
  class="exec-evaluator-container flex flex-col gap-y-2 shadow-[0px_1px_1px_1px_lightgray] p-1 rounded"
>
  <div class="user-input-header flex text-gray-600 italic gap-x-2 text-sm">
    <div class="flex-1 flex justify-center bg-slate-100 relative">
      Name
      <button
        class="delete-button hidden absolute top-1/2 -translate-y-1/2 left-0 opacity-60 hover:opacity-100"
        onclick={() => handleDelete()}
      >
        <img src="trash.svg" alt="delete" class="w-4 h-4" />
      </button>
    </div>
    <div
      class="header-description flex-2 flex justify-center bg-slate-100 relative"
    >
      Definition
    </div>
  </div>
  <div class="user-input flex text-slate-700 gap-x-2 text-sm">
    <div
      use:trim
      class="user-input-name flex-1 flex justify-center"
      contenteditable
      onblur={() => {
        const name = document.querySelector(".user-input-name")?.textContent;
        evaluator.name = name || "";
      }}
    >
      {evaluator.name}
    </div>
    <div
      use:trim
      class="user-input-description flex-2 flex justify-center"
      contenteditable
      onblur={() => {
        const description = document.querySelector(
          ".user-input-description"
        )?.textContent;
        evaluator.definition = description || "";
      }}
    >
      {evaluator.definition}
    </div>
  </div>
  <div
    class="task-option-container flex gap-x-2 items-center px-2 text-sm text-slate-700"
  >
    <div class="">Target:</div>
    <div class="options flex gap-2 flex-wrap text-sm">
      {#each tasks as task}
        <button
          class:selected={evaluator.task === task[0]}
          class="flex gap-x-2 outline-2 outline-gray-100 px-2 py-0.5 rounded text-slate-400 hover:bg-slate-200 hover:text-slate-700"
          onclick={() => (evaluator.task = task[0])}
        >
          {task[1]}
        </button>
      {/each}
    </div>
  </div>
  <div class="flex flex-col">
    <button
      class="text-slate-600 italic bg-slate-100 flex justify-center relative hover:bg-slate-200"
      onclick={() => (show_parameters = !show_parameters)}
    >
      Parameters
      <img
        src="chevron_down.svg"
        alt="expand"
        class="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4"
      />
    </button>
    {#if show_parameters}
      <div class="" in:slide>
        {#if evaluator.parameters}
          <div>
            <PromptTemplate messages={evaluator.parameters.prompt_template}
            ></PromptTemplate>
          </div>
        {:else if loading}
          <div class="flex grow justify-center mt-2">
            <img
              src="loader_circle.svg"
              alt="loading"
              class="w-4 h-4 animate-spin"
            />
          </div>
        {:else}
          <div class="px-2 italic text-gray-500 text-sm">
            Enter the name and description then click "Generate Evaluator"
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style lang="postcss">
  @reference "../app.css";
  .user-input-name:empty:before {
    content: "Name the evaluator...";
    color: gray;
    pointer-events: none;
  }
  .user-input-description:empty:before {
    content: "Describe the evaluation criteria...";
    color: gray;
    pointer-events: none;
  }
  .user-input-name:focus,
  .user-input-description:focus {
    @apply justify-start;
  }
  .exec-evaluator-container:hover {
    & .delete-button {
      @apply flex;
    }
  }
  .disabled {
    @apply cursor-not-allowed opacity-50 outline-none;
  }
  .disabled-button {
    pointer-events: none;
  }
  .selected {
    @apply bg-slate-200 text-slate-700;
  }
</style>
