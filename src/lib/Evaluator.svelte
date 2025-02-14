<script lang="ts">
  import { slide } from "svelte/transition";
  import type { Snippet } from "svelte";

  let {
    title,
    few_shot_examples,
    icon,
  }: { title: string; few_shot_examples: any; icon: Snippet } = $props();
  let show = $state(false);
</script>

<div class="flex flex-col px-1 gap-y-1">
  <div
    role="button"
    tabindex="0"
    class="header-2 flex gap-x-2"
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
    <div in:slide class="flex flex-col gap-y-2">
      Definition here!
      {#each few_shot_examples as example}
        <div class="flex gap-x-2 items-center text-gray-500">
          <div class="font-mono text-sm min-w-[4rem]">{example.task_label}</div>
          <div class="max-h-[15rem] overflow-auto">
            {example.user_evaluation}
          </div>
          <div class="max-h-[15rem] overflow-auto">
            {example.llm_evaluation}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-orange-100 flex items-center border-b-2 border-orange-200 hover:border-2;
  }
</style>
