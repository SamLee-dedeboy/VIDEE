<script lang="ts">
  import { getContext, onMount } from "svelte";
  import type { tExecutionEvaluatorResult } from "types";
  import { UncertaintyGraph } from "renderer/UncertaintyGraph";
  import { server_address } from "constants";
  let { result }: { result: tExecutionEvaluatorResult } = $props();
  const svgId = "evaluator-result-radial-chart-svg";
  let uncertaintyGraph: UncertaintyGraph = new UncertaintyGraph(svgId);
  const session_id = (getContext("session_id") as Function)();

  $effect(() => {
    fetchDR(result);
  });

  function fetchDR(_result: tExecutionEvaluatorResult) {
    console.log($state.snapshot(_result));
    fetch(`${server_address}/primitive_task/evaluators/result/dr/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id,
        data: _result.result.documents,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Evaluation result distribution:", data);
        updateRadialChart(data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function updateRadialChart(dr_result) {
    let highlight_ids: string[] | undefined = undefined;
    console.log({ dr_result, highlight_ids });
    uncertaintyGraph.update(dr_result, highlight_ids);
  }

  onMount(() => {
    uncertaintyGraph.init();
  });
</script>

<div class="flex flex-col aspect-square bg-gray-50 px-4">
  <svg id={svgId} class="w-full h-full"> </svg>
</div>
