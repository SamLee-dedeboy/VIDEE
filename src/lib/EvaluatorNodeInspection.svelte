<script lang="ts">
  import { slide } from "svelte/transition";
  import PromptTemplate from "./PromptTemplate.svelte";
  import { trim } from "lib/trim";
  import type { tExecutionEvaluator } from "types";
  let {
    evaluator = $bindable(),
  }: {
    evaluator: tExecutionEvaluator;
  } = $props();
  let show_parameters = $state(false);
</script>

<div class="flex flex-col">
  <button
    class="text-slate-600 italic bg-slate-100 flex justify-center relative hover:bg-slate-200"
    onclick={() => (show_parameters = !show_parameters)}
  >
    Parameters
    <img
      src="chevron_down.svg"
      alt="expand"
      class="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4"
    />
  </button>
  {#if show_parameters}
    <div class="" in:slide>
      {#if evaluator.parameters}
        <div>
          <PromptTemplate messages={evaluator.parameters.prompt_template}
          ></PromptTemplate>
        </div>
      {:else}
        <div class="px-2 italic text-gray-500 text-sm">
          Something went wrong...
        </div>
      {/if}
    </div>
  {/if}
</div>

<style lang="postcss">
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
