<script lang="ts">
  import { slide } from "svelte/transition";
  let { document } = $props();
  let show_full_content = $state(false);
</script>

<div
  class="doc-container flex flex-col outline-1 outline-gray-200 rounded px-1 divide-y"
>
  {#each Object.keys(document) as doc_input_key}
    {#if doc_input_key === "content"}
      <div class="flex gap-x-2 items-center">
        <div class="font-mono text-sm text-gray-500">
          {doc_input_key}
        </div>
        {#if show_full_content}
          <div class="relative">
            <div
              in:slide
              class="doc-content doc-content-full max-h-[15rem] overflow-auto whitespace-pre-line pr-3"
            >
              {document[doc_input_key]}
            </div>
            <button
              class="doc-content-close absolute right-0 bottom-[100%] p-0.5 rounded-full z-10"
              onclick={() => (show_full_content = false)}
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
              onclick={() => (show_full_content = true)}
              onkeyup={() => {}}
            >
              {document[doc_input_key]}
            </button>
          </div>
        {/if}
      </div>
    {:else}
      <div class="flex gap-x-2 items-center text-gray-500">
        <div class="font-mono text-sm min-w-[4rem]">
          {doc_input_key}
        </div>
        <div class="max-h-[15rem] overflow-auto">
          {document[doc_input_key]}
        </div>
      </div>
    {/if}
  {/each}
</div>

<style lang="postcss">
  @reference "../app.css";
  .doc-content {
    @apply italic text-sm text-gray-600 pl-1;
  }
  .doc-container {
    background: var(--bg-color);
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
