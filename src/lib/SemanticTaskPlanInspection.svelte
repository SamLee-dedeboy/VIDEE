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
  let {
    few_shot_examples,
    semantic_tasks,
  }: {
    few_shot_examples: Record<string, any>;
    semantic_tasks: tSemanticTask[];
  } = $props();
  const session_id = (getContext("session_id") as Function)();
  let documents: any[] = $state([]);
  let eval_definitions: Record<string, string> = $state({
    complexity: "The complexity of the task",
    coherence: "The coherence of the task",
    importance: "The importance of the task",
  });

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
  function getEvalDefinitions() {
    fetch(`${server_address}/eval/definitions/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log({ eval_definitions: data });
        eval_definitions = data;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function updateEvalDefinitions(_eval_definitions: Record<string, string>) {
    fetch(`${server_address}/eval/definitions/update/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id, eval_definitions: _eval_definitions }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  onMount(() => {
    getDocuments();
    getEvalDefinitions();
  });
</script>

{#snippet complexity_icon()}
  <img src="network.svg" alt="complexity" class="w-6 h-6 pointer-events-none" />
{/snippet}

{#snippet coherence_icon()}
  <img src="waveform.svg" alt="coherence" class="w-6 h-6 pointer-events-none" />
{/snippet}

{#snippet importance_icon()}
  <img src="cpu.svg" alt="importance" class="w-6 h-6 pointer-events-none" />
{/snippet}

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
  <ExecutionEvaluators --bg-color="#ffedd4" tasks={semantic_tasks}
  ></ExecutionEvaluators>
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-orange-100 flex items-center border-b-2 border-orange-200 hover:border-2;
  }
</style>
