<script lang="ts">
  import { slide } from "svelte/transition";
  import type { Snippet } from "svelte";

  let { title, icon }: { title: string; icon: Snippet } = $props();
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
    <div in:slide class="flex flex-col gap-y-2">Definition here!</div>
  {/if}
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-orange-100 flex items-center border-b-2 border-orange-200 hover:border-2;
  }
</style>
