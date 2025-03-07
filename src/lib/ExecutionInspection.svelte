<script lang="ts">
  import { server_address } from "constants";
  import { slide } from "svelte/transition";
  import { onMount, setContext } from "svelte";
  import type {
    tExecutionEvaluator,
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
    tSemanticTask,
  } from "types";
  import { getContext } from "svelte";
  import DocumentCard from "./DocumentCard.svelte";
  import PrimitiveTaskInspection from "./PrimitiveTaskInspection.svelte";
  import EvaluatorNodeInspection from "./EvaluatorNodeInspection.svelte";
  import DatasetInspection from "./DatasetInspection.svelte";
  let {
    primitive_task,
    evaluator_node,
  }: {
    primitive_task:
      | (tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>)
      | undefined;
    evaluator_node: tExecutionEvaluator | undefined;
  } = $props();
  const session_id = (getContext("session_id") as Function)();
  let documents: any[] = $state([]);

  let inspect_mode = $state("task");
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
  <DatasetInspection></DatasetInspection>
  {#if primitive_task}
    <div in:slide>
      <PrimitiveTaskInspection task={primitive_task}></PrimitiveTaskInspection>
    </div>
  {/if}
  {#if evaluator_node}
    <div in:slide>
      <EvaluatorNodeInspection evaluator={evaluator_node}
      ></EvaluatorNodeInspection>
    </div>
  {/if}
  <!-- <ExecutionEvaluators --bg-color="#ffedd4" tasks={semantic_tasks}
  ></ExecutionEvaluators> -->
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-gray-100 flex items-center justify-center border-b-2 border-gray-200 hover:border-2;
  }
  .header-3 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-gray-200 flex items-center justify-center outline-gray-200;
  }
  .disabled {
    @apply text-gray-400  pointer-events-none opacity-50;
  }
</style>
