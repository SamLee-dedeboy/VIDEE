<script lang="ts">
  import type { tDocument } from "types";
  import { slide } from "svelte/transition";
  import DocumentCard from "./DocumentCard.svelte";
  import { setContext } from "svelte";
  let {
    documents,
    bg_color = "#f8f8f8",
    bg_hover_color = "#e3e3e3",
  }: {
    documents: tDocument[];
    bg_color?: string;
    bg_hover_color?: string;
  } = $props();
  const page_size = 50;
  let paged_documents = $derived.by(() => {
    let result: tDocument[][] = [];
    for (let i = 0; i < documents.length; i += page_size) {
      result.push(documents.slice(i, i + page_size));
    }
    return result;
  });

  let page = $state(0);

  export function navigateToDoc(doc: tDocument) {
    console.log("clicked: ", doc.id);
    // get the index of the doc
    const doc_index = documents.map((d) => d.id).indexOf(doc.id);
    if (doc_index !== -1) {
      // get the page number
      page = Math.floor(doc_index / page_size);
      document
        .querySelector(".doc-container.highlighted")
        ?.classList.remove("highlighted");
      setTimeout(() => {
        const doc_card = document.querySelector(
          `.doc-container[data-attribute-id="${doc.id}"]`
        );
        console.log("doc_card: ", doc_card);
        if (doc_card) {
          doc_card.classList.add("highlighted");
          doc_card.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 100);
    }
  }

  setContext("navigate_to_doc", navigateToDoc);
</script>

<div
  in:slide
  class="flex flex-col gap-y-2 max-h-[25rem] overflow-auto pr-3 pl-0.5 py-1"
>
  {#each paged_documents[page] as document}
    <DocumentCard
      {document}
      --bg-color={bg_color}
      --bg-hover-color={bg_hover_color}
    />
  {/each}
  <!-- {#each documents as document}
          <DocumentCard
            {document}
            --bg-color="#f8f8f8"
            --bg-hover-color="#e3e3e3"
          />
        {/each} -->
</div>
<div class="pagination flex justify-between gap-x-2 text-slate-600 pr-3 mt-2">
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
    {#each paged_documents as _, p}
      <button
        class=" hover:bg-gray-200 flex justify-center py-2 px-1 rounded text-sm"
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
    class:disabled={page === paged_documents.length - 1}
    onclick={() => {
      page += 1;
    }}
  >
    <img src="arrow-right.svg" alt="next" class="w-4 h-4" />
  </button>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .active {
    @apply bg-gray-200;
  }
</style>
