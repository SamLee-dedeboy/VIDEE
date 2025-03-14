<script lang="ts">
  import { slide } from "svelte/transition";
  import type { Snippet } from "svelte";
  import type { tSemanticTask } from "types";
  import { evaluation_colors } from "constants";

  let {
    title,
    definition = $bindable(""),
    few_shot_examples,
    icon,
    handleDefinitionChanged = () => {},
  }: {
    title: string;
    definition: string;
    few_shot_examples: {
      node: tSemanticTask;
      parent_node: tSemanticTask;
      user_evaluation: boolean;
      llm_evaluation: boolean;
      user_reasoning: string | undefined;
    }[];
    icon: Snippet;
    handleDefinitionChanged: Function;
  } = $props();
  let show = $state(false);
</script>

<div class="container flex flex-col gap-y-1 rounded" class:expanded={show}>
  <div
    role="button"
    tabindex="0"
    class="header-2 flex gap-x-2"
    class:expanded={show}
    onclick={() => {
      show = !show;
    }}
    onkeyup={() => {}}
  >
    {@render icon()}
    {title}
    <img src="chevron_down.svg" alt="expand" class="hidden ml-auto w-5 h-5" />
  </div>

  {#if show}
    <div in:slide class="flex flex-col px-1 gap-y-2 select-none">
      <div class="flex flex-col">
        <div class="text-gray-400 header-3">Definition</div>
        <div
          contenteditable
          class="px-1 rounded text-slate-600"
          onblur={(e) => handleDefinitionChanged(e.target.textContent.trim())}
        >
          {definition}
        </div>
      </div>
      <div class="flex flex-col">
        <div class="header-3">User Changes</div>
        <div
          class="grid grid-cols-[1fr_1fr_2fr] gap-2 bg-slate-100 border-b border-slate-300"
        >
          <div class="table-header">Label</div>
          <div class="table-header">Should be</div>
          <div class="table-header">Explanation</div>
        </div>
        <div
          class="grid grid-cols-[1fr_1fr_2fr] gap-y-2 divide-y divide-gray-200"
        >
          {#each few_shot_examples as example}
            <div class="table-item text-sm text-center">
              {example.node.label}
            </div>
            <div class="table-item text-sm">
              <svg class="w-5 h-5" viewBox="0 0 10 10">
                <circle
                  cx="5"
                  cy="5"
                  r="4"
                  fill={example.user_evaluation
                    ? evaluation_colors.good
                    : evaluation_colors.bad}
                />
              </svg>
              {example.user_evaluation ? "Good" : "Bad"}
            </div>
            <div class="table-item text-sm">
              {example.user_reasoning ? example.user_reasoning : "N/A"}
            </div>
          {/each}
        </div>
        <!-- <div
          class="flex gap-x-2 items-center bg-slate-100 border-b border-slate-300"
        >
          <div
            class="w-[10rem] flex justify-center shrink-0 italic text-slate-500"
          >
            Label
          </div>
          <div class="min-w-[6rem] flex justify-center italic text-slate-500">
            Should be
          </div>
          <div class="min-w-[6rem] flex justify-center italic text-slate-500">
            Explanation
          </div>
        </div> -->
        <!-- <div class="flex flex-col divide-y">
          {#each few_shot_examples as example}
            <div class="flex gap-x-2 text-gray-500">
              <svg class="w-6 h-6 shrink-0" viewBox="0 0 10 10">
                <circle
                  cx="5"
                  cy="5"
                  r="4"
                  fill={example.user_evaluation
                    ? evaluation_colors.good
                    : evaluation_colors.bad}
                />
              </svg>
              <div class="w-[8.5rem] flex justify-start shrink-0 gap-x-2">
                {example.node.label}
              </div>
              <div class="min-w-[6rem] flex justify-center">
                {example.user_evaluation ? "Good" : "Bad"}
              </div>
              <div
                class="min-w-[8rem] flex justify-center italic text-slate-500"
              >
                {example.user_reasoning ? example.user_reasoning : "N/A"}
              </div>
            </div>
          {/each}
        </div> -->
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .container.expanded {
    @apply border-l-8 border-slate-400 shadow-[0px_1px_1px_1px_gray];
  }
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-slate-200 flex items-center border-b-2 border-slate-400 hover:border-2;
  }
  .header-3 {
    @apply font-mono text-slate-600 px-1 flex items-center border-b-2 border-slate-400;
  }
  .table-header {
    @apply flex justify-center italic text-slate-500;
  }
  .table-item {
    @apply flex justify-center italic text-slate-500 gap-x-1;
  }

  .few-shot-description[data-attribute-truncate] {
    @apply max-h-[1.5rem] overflow-hidden;
  }
  .few-shot-description[data-attribute-truncate]:after {
    content: "...";
  }
  div[contenteditable]:hover {
    @apply ring-2 ring-blue-300;
  }
</style>
