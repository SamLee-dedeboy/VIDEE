<script lang="ts">
  import { slide } from "svelte/transition";
  
  let {
    items,
    bg_color = "#f8f8f8",
    bg_hover_color = "#e3e3e3",
  }: {
    items: any[];
    bg_color?: string;
    bg_hover_color?: string;
  } = $props();

  const page_size = 50;
  let paged_items = $derived.by(() => {
    let result: any[][] = [];
    for (let i = 0; i < items.length; i += page_size) {
      result.push(items.slice(i, i + page_size));
    }
    return result;
  });

  let page = $state(0);
  
  // Track which items have expanded views
  let expanded_items = $state<Record<string, boolean>>({});
  
  function toggleExpand(index: number) {
    const itemKey = `${page}-${index}`;
    expanded_items[itemKey] = !expanded_items[itemKey];
  }
  
  function isExpanded(index: number): boolean {
    const itemKey = `${page}-${index}`;
    return !!expanded_items[itemKey];
  }
  
  // Helper function to format values nicely
  function formatValue(value: any): string {
    if (value === null) return "null";
    if (value === undefined) return "undefined";
    if (typeof value === "object") {
      return JSON.stringify(value, null, 2).replace(/['"]+/g, "");
    }
    return String(value);
  }
</script>

<div
  in:slide
  class="flex flex-col gap-y-2 max-h-[25rem] overflow-auto pr-3 pl-0.5 py-1"
>
  {#each paged_items[page] as item, index}
    <div 
      class="item-container flex flex-col outline-1 outline-gray-200 rounded px-1 divide-y"
      style="--bg-color: {bg_color}; --bg-hover-color: {bg_hover_color};"
    >
      <div class="flex gap-x-2 items-center">
        <div class="font-mono text-sm text-gray-500 min-w-[4rem]">
          #{page * page_size + index}
        </div>
        {#if isExpanded(index)}
          <div class="relative w-full">
            <div in:slide class="doc-content doc-content-full max-h-[15rem] overflow-auto whitespace-pre-line pr-3">
              {formatValue(item)}
            </div>
            <button
              class="doc-content-close absolute right-0 top-0 p-0.5 rounded-full z-10"
              title="close"
              onclick={() => toggleExpand(index)}
            >
              <img
                src="panel_top_close.svg"
                alt="close"
                class="w-5 h-5 pointer-events-none"
              />
            </button>
          </div>
        {:else}
          <div class="relative grow min-h-[1.5rem]">
            <button
              tabindex="0"
              class="doc-content doc-content-short truncate absolute left-0 right-0 top-0 bottom-0"
              title="expand"
              onclick={() => toggleExpand(index)}
              onkeyup={() => {}}
            >
              {formatValue(item)}
            </button>
          </div>
        {/if}
      </div>
    </div>
  {/each}
</div>

{#if paged_items.length > 1}
  <div class="pagination flex justify-between gap-x-2 text-slate-600 pr-3">
    <button
      class="w-[2rem] shrink-0 hover:bg-gray-100 flex justify-center items-center py-1 rounded outline-2 outline-gray-200 text-sm"
      title="previous"
      class:disabled={page === 0}
      onclick={() => {
        page -= 1;
      }}
    >
      <img src="arrow-left.svg" alt="previous" class="w-4 h-4" />
    </button>
    <div class="flex items-center overflow-x-auto pb-3">
      {#each paged_items as _, p}
        <button
          class="hover:bg-gray-200 flex justify-center py-2 px-1 rounded text-sm"
          class:active={page === p}
          onclick={() => {
            page = p;
          }}
        >
          {p + 1}
        </button>
      {/each}
    </div>
    <button
      class="w-[2rem] shrink-0 hover:bg-gray-100 flex justify-center items-center py-1 rounded outline-2 outline-gray-200 text-sm"
      title="next"
      class:disabled={page === paged_items.length - 1}
      onclick={() => {
        page += 1;
      }}
    >
      <img src="arrow-right.svg" alt="next" class="w-4 h-4" />
    </button>
  </div>
{/if}

<style lang="postcss">
  @reference "tailwindcss";
  .active {
    @apply bg-blue-100 font-bold;
  }
  .disabled {
    @apply opacity-50 cursor-not-allowed;
  }
  .item-container {
    background: var(--bg-color);
  }
  .doc-content {
    @apply italic text-sm text-gray-600 pl-1;
  }
  .doc-content-short:hover {
    background: var(--bg-hover-color);
  }
  .doc-content-close {
    background: var(--bg-color);
  }
  .doc-content-close:hover {
    background: var(--bg-hover-color);
  }
</style> 