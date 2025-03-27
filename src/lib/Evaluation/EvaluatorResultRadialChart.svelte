<script lang="ts">
  import { getContext, onMount } from "svelte";
  import type { tDRResult, tExecutionEvaluatorResult, tDocument } from "types";
  import { RadialEvaluationChart } from "renderer/RadialEvaluationChart";
  import { server_address } from "constants";
  import { session_id } from "lib/ExecutionStates.svelte";
  let { result }: { result: tExecutionEvaluatorResult } = $props();
  const svgId = "evaluator-result-radial-chart-svg";
  let evaluationChart: RadialEvaluationChart = new RadialEvaluationChart(svgId);

  let show_topic_labels = $state(true);
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
    evaluationChart.updateTopicLabels(show_topic_labels);
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

<div class="flex flex-col aspect-square bg-gray-50 px-4 relative">
  <div
    class="absolute top-0 right-0 font-mono px-1 py-0.5 transition-all flex items-center gap-x-1 text-slate-600"
  >
    <button
      aria-label="Toggle topic labels"
      onclick={() => {
        show_topic_labels = !show_topic_labels;
        evaluationChart.updateTopicLabels(show_topic_labels);
      }}
    >
      <svg class="w-4 h-4" viewBox="0 0 12 12"
        ><circle
          cx="6"
          cy="6"
          r="5"
          fill={show_topic_labels ? "#7be9c6" : "none"}
          stroke="gray"
        ></circle></svg
      >
    </button>
    Topic Labels
  </div>
  <svg id={svgId} class="w-full h-full"> </svg>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .active {
    @apply text-slate-600 bg-gray-50 hover:bg-gray-300;
  }
  .disabled {
    @apply text-gray-300 bg-gray-100 hover:bg-gray-50 hover:text-slate-600;
  }
</style>
