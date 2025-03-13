<script lang="ts">
  import { server_address } from "constants";
  import { getContext, onMount, setContext, tick } from "svelte";
  import { slide } from "svelte/transition";
  import type { tDocument, tDRResult } from "types";
  import DocumentCard from "./DocumentCard.svelte";
  import { RadialTopicChart } from "renderer/RadialTopicChart";
  import PagedDocuments from "./PagedDocuments.svelte";
  let show_documents = $state(false);
  let show_topics = $state(false);
  let documents: tDocument[] = $state([]);
  let dr_result: tDRResult[] = $state([]);
  let paged_document_component: any = $state();
  const session_id = (getContext("session_id") as Function)();
  const svgId = "radial-topic-chart-svg";
  let topicChart: RadialTopicChart = new RadialTopicChart(svgId);

  $effect(() => {
    if (show_topics) {
      topicChart.clear();
      topicChart.update(dr_result, undefined);
    }
  });

  let loading_topics = $state(false);
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
        fetchDR(documents);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function fetchDR(_documents: tDocument[]) {
    loading_topics = true;
    fetch(`${server_address}/documents/dr/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id, data: _documents }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("DR result:", data);
        dr_result = data;
        loading_topics = false;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  // function handleDocumentMouseover(doc: tDocument) {
  //   console.log("mouseover: ", doc);
  //   hovered_document = doc;
  // }

  // function handleDocumentMouseout(doc: tDocument) {
  //   console.log("mouseover: ", doc);
  //   hovered_document = undefined;
  // }

  function handleDocumentClicked(doc: tDocument) {
    show_documents = true;
    paged_document_component.navigateToDoc(doc);
  }

  // async function navigateToDoc(doc: tDocument) {
  // }
  // setContext("navigate_to_doc", navigateToDoc);

  onMount(() => {
    topicChart.init();
    // topicChart.on("node_mouseover", handleDocumentMouseover);
    // topicChart.on("node_mouseout", handleDocumentMouseout);
    topicChart.on("node_clicked", handleDocumentClicked);
    getDocuments();
  });
</script>

<div class="flex flex-col gap-y-2">
  <div
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-gray-100 flex justify-center"
  >
    Dataset
  </div>
  <div class="flex flex-col px-1 gap-y-1">
    <div
      role="button"
      tabindex="0"
      class="header-2"
      onclick={() => {
        show_documents = !show_documents;
      }}
      onkeyup={() => {}}
    >
      Documents
      <img src="chevron_down.svg" alt="expand" class="hidden ml-auto w-5 h-5" />
    </div>

    {#if show_documents}
      <PagedDocuments bind:this={paged_document_component} {documents} />
    {/if}
  </div>
  <div class="flex flex-col gap-y-2 px-1">
    <div
      role="button"
      tabindex="0"
      class="header-2"
      class:disabled={loading_topics}
      onclick={() => (show_topics = !show_topics)}
      onkeyup={() => {}}
    >
      {#if loading_topics}
        <img
          src="loader_circle.svg"
          class="w-6 h-6 animate-spin opacity-50"
          alt="loading"
        />
      {/if}
      Topics
      <img src="chevron_down.svg" alt="expand" class="hidden ml-auto w-5 h-5" />
    </div>
    <div
      class="flex flex-col aspect-square bg-gray-50 px-4 transition-all max-h-auto"
      class:hide={!show_topics}
    >
      <svg id={svgId} class="topic-chart-svg w-full h-full"> </svg>
    </div>
  </div>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-gray-100 flex items-center border-b-2 border-slate-200 hover:border-2;
  }
  .hide {
    @apply max-h-0;
  }
  .disabled {
    @apply opacity-50 pointer-events-none;
  }
  .pagination::-webkit-scrollbar {
    width: 2px;
    height: 2px;
  }
  .active {
    @apply bg-gray-200;
  }

  .pagination::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 3px;
  }

  .topic-chart-svg {
    & :global(.node-hover) {
      stroke: black;
    }
  }
</style>
