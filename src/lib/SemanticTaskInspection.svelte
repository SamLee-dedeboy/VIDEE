<script lang="ts">
  import { server_address } from "constants";
  import { slide } from "svelte/transition";
  import { onMount, setContext } from "svelte";
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
  } from "types";
  import { getContext } from "svelte";
  import DocumentCard from "./DocumentCard.svelte";
  const session_id = (getContext("session_id") as Function)();
  let documents: any[] = $state([]);
  let show_documents = $state(false);

  function getDocuments() {
    fetch(`${server_address}/documents/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        documents = data;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  onMount(() => {
    getDocuments();
  });
</script>

<div class="flex flex-col px-1 gap-y-1">
  <div
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-orange-100 flex justify-center"
  >
    Inspection
  </div>
  <div class="flex flex-col px-1 gap-y-1">
    <div
      role="button"
      tabindex="0"
      class="header-2"
      onclick={() => {
        show_documents = !show_documents;
      }}
    >
      Documents
      <img src="chevron_down.svg" alt="expand" class="hidden ml-auto w-5 h-5" />
    </div>

    {#if show_documents}
      <div in:slide class="flex flex-col gap-y-2">
        {#each documents as document}
          <DocumentCard
            {document}
            --bg-color="oklch(0.98 0.016 73.684)"
            --bg-hover-color="oklch(0.901 0.076 70.697)"
          />
        {/each}
      </div>
    {/if}
  </div>
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 bg-orange-100 px-1 cursor-pointer hover:bg-orange-200 flex items-center;
  }
</style>
