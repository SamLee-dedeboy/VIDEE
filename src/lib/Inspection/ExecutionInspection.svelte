<script lang="ts">
  import { server_address } from "constants";
  import { slide } from "svelte/transition";
  import { onMount, setContext, tick } from "svelte";
  import type { tExecutionEvaluator, tPrimitiveTask } from "types";
  import { getContext } from "svelte";
  import PrimitiveTaskInspection from "./PrimitiveTaskInspection.svelte";
  import EvaluatorNodeInspection from "./EvaluatorNodeInspection.svelte";
  import DatasetInspection from "./DatasetInspection.svelte";
  let {
    primitive_task,
    evaluator_node,
  }: {
    primitive_task: tPrimitiveTask | undefined;
    evaluator_node: tExecutionEvaluator | undefined;
  } = $props();
  const session_id = (getContext("session_id") as Function)();
  let documents: any[] = $state([]);

  let primitive_task_inspection_panel: any = $state();

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
  export function scrollIntoInspectionPanel() {
    document.querySelector(".inspection-container")?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }

  export async function navigate_to_primitive_task_results() {
    await tick();
    primitive_task_inspection_panel.navigate_to_results();
  }

  onMount(() => {
    getDocuments();
  });
</script>

<div class="flex flex-col px-1 gap-y-4">
  <DatasetInspection></DatasetInspection>
  {#if primitive_task}
    <div in:slide class="inspection-container">
      <PrimitiveTaskInspection
        bind:this={primitive_task_inspection_panel}
        task={primitive_task}
      ></PrimitiveTaskInspection>
    </div>
  {/if}
  {#if evaluator_node}
    <div in:slide class="inspection-container">
      <EvaluatorNodeInspection evaluator={evaluator_node}
      ></EvaluatorNodeInspection>
    </div>
  {/if}
</div>
