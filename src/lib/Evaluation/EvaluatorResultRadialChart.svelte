<script lang="ts">
  import { getContext, onMount } from "svelte";
  import type { tDRResult, tExecutionEvaluatorResult, tDocument } from "types";
  import { RadialEvaluationChart } from "renderer/RadialEvaluationChart";
  import { server_address } from "constants";
  import { session_id } from "lib/ExecutionStates.svelte";
  let { result }: { result: tExecutionEvaluatorResult } = $props();
  const svgId = "evaluator-result-radial-chart-svg";
  let evaluationChart: RadialEvaluationChart = new RadialEvaluationChart(svgId);

  $effect(() => {
    fetchDR(result);
  });

  function fetchDR(_result: tExecutionEvaluatorResult) {
    console.log($state.snapshot(_result));
    fetch(`${server_address}/documents/dr/`, {
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
        console.log("DR result:", data);
        updateRadialChart(data, _result);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function updateRadialChart(
    dr_result: (tDRResult & tDocument)[],
    evaluation_result: tExecutionEvaluatorResult
  ) {
    const evaluator_name = result.name;
    const evaluator_output_key = evaluator_name + "_output";
    const reduce_result = evaluation_result.result.documents.reduce(
      (acc, doc) => {
        acc["doc_id_to_score"][doc.id] = doc[evaluator_output_key];
        if (!acc["score_frequency"][doc[evaluator_output_key]]) {
          acc["score_frequency"][doc[evaluator_output_key]] = 0;
        }
        acc["score_frequency"][doc[evaluator_output_key]] += 1;
        return acc;
      },
      {
        doc_id_to_score: {},
        score_frequency: {},
      }
    );
    // this should be replaced with real ensemble scores
    dr_result.forEach((doc) => {
      doc.value = reduce_result["doc_id_to_score"][doc.id] || 0;
    });
    evaluation_result.possible_scores = evaluation_result.possible_scores.sort(
      (a, b) =>
        (reduce_result["score_frequency"][a] || 0) -
        (reduce_result["score_frequency"][b] || 0)
    );
    evaluationChart.update(dr_result, evaluation_result, undefined);
  }

  const navigateToDoc: (doc: tDocument) => void = getContext("navigate_to_doc");
  function handleDocumentClicked(doc: tDocument) {
    navigateToDoc(doc);
  }

  onMount(() => {
    evaluationChart.init();
    evaluationChart.on("node_clicked", handleDocumentClicked);
  });
</script>

<div class="flex flex-col aspect-square bg-gray-50 px-4">
  <svg id={svgId} class="w-full h-full"> </svg>
</div>
