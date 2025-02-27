<script lang="ts">
  import { server_address } from "constants";
  import { slide } from "svelte/transition";
  import { onMount, setContext } from "svelte";
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
    tSemanticTask,
  } from "types";
  import { getContext } from "svelte";
  import DocumentCard from "./DocumentCard.svelte";
  import Evaluator from "./Evaluator.svelte";
  import ExecutionEvaluators from "./ExecutionEvaluators.svelte";
  import PrimitiveTaskInspection from "./PrimitiveTaskInspection.svelte";
  let {
    semantic_tasks,
    primitive_task,
  }: {
    semantic_tasks: tSemanticTask[];
    primitive_task:
      | (tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>)
      | undefined;
  } = $props();
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

<div class="flex flex-col px-1 gap-y-4">
  <div class="flex flex-col gap-y-2">
    <div
      class="text-[1.5rem] text-slate-600 font-semibold italic bg-orange-100 flex justify-center"
    >
      Dataset Inspection
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
        <img
          src="chevron_down.svg"
          alt="expand"
          class="hidden ml-auto w-5 h-5"
        />
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
  {#if primitive_task}
    <PrimitiveTaskInspection task={primitive_task}></PrimitiveTaskInspection>
  {/if}
  <!-- <ExecutionEvaluators --bg-color="#ffedd4" tasks={semantic_tasks}
  ></ExecutionEvaluators> -->
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-orange-100 flex items-center border-b-2 border-orange-200 hover:border-2;
  }
</style>
