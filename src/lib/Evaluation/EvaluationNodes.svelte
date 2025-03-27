<script lang="ts">
  import { getContext, onMount, setContext, tick } from "svelte";
  import type { tExecutionEvaluator, tPrimitiveTask, tNode } from "types";
  import ExecutionEvaluatorCard from "./ExecutionEvaluatorCard.svelte";
  import AddExecutionEvaluator from "../Execution/AddExecutionEvaluator.svelte";
  import { server_address } from "constants";
  import * as d3 from "d3";
  import { DAG } from "renderer/dag";
  import { evaluatorState, session_id } from "../ExecutionStates.svelte";
  let {
    tasks,
    generating_recommendations,
    handleGenerateRecommendations = () => {},
    handleInspectEvaluatorNode = () => {},
  }: {
    tasks: tPrimitiveTask[];
    generating_recommendations: boolean;
    handleGenerateRecommendations: Function;
    handleInspectEvaluatorNode: Function;
  } = $props();
  const evaluators = $derived(evaluatorState.evaluators);
  let evaluator_node_expanded: string[] = $state([]);
  let loading = $state(false);
  let adding_evaluator = $state(false);
  let generating_for_description = $state("");
  let ask_to_check_results = $state(false);

  let executing_evaluator_name: string | undefined = $state(undefined);
  let executed_evaluator_name: string | undefined = $state(undefined);
  const svgId = "evaluation-dag-svg";
  const node_size: [number, number] = [150, 80];
  let dag_renderer = new DAG(
    svgId,
    node_size,
    ".evaluator-card-container",
    ".evaluator-nodes"
  );
  $effect(() => {
    update_dag(evaluators);
  });
  export function rerender_evaluation() {
    update_dag(evaluators);
  }
  /**
   * Prepare the data for the dag renderer
   * by adding the bounding box of each task card
   * @param _primitive_tasks
   */
  async function update_dag(_evaluator_nodes: tExecutionEvaluator[]) {
    // await tick();
    console.log("updating evaluator dag:", _evaluator_nodes);
    // get the bounding box of each task card
    const evaluator_card_divs: NodeListOf<HTMLElement> =
      document.querySelectorAll(".evaluator-card-container");
    const dag_data: tNode[] = Array.from(evaluator_card_divs).map(
      (div, index) => {
        const id = (div as HTMLElement).dataset.id;
        // const parentIds =
        //   index === 0
        //     ? []
        //     : [evaluator_card_divs[index - 1].dataset.id as string];
        const node_data: tExecutionEvaluator = _evaluator_nodes.find(
          (evaluator) => evaluator.name === id
        )!;

        const parentIds = node_data.isRoot
          ? []
          : [evaluator_card_divs[index - 1].dataset.id as string]; // this works because the evaluators are sorted
        const transform_scale =
          div.style.transform === ""
            ? 1
            : d3.zoomTransform(d3.select(`#${svgId}`).node()).k;
        console.log(id, div.getBoundingClientRect(), transform_scale);
        return {
          id: node_data.name,
          parentIds: parentIds,
          ...node_data,
          data: node_data,
          bbox: {
            width: div.getBoundingClientRect().width / transform_scale,
            height: div.getBoundingClientRect().height / transform_scale,
          },
        };
      }
    );
    // call renderer
    dag_renderer.update(dag_data, [], undefined, false, true, true);
  }

  function handleAddEvaluator() {
    adding_evaluator = true;
  }

  function handleGenerateEvaluator(description: string, task_id: string) {
    adding_evaluator = false;
    loading = true;
    console.log(
      "Generating evaluator",
      description,
      tasks.find((t) => t.id === task_id),
      session_id
    );
    generating_for_description = description;
    fetch(`${server_address}/primitive_task/evaluators/add/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        task: tasks.find((t) => t.id === task_id),
        description,
        session_id,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
        data["result"]["recommendation"] = false;
        evaluatorState.evaluators = [...evaluators, data["result"]];
        update_dag(evaluators);
        updateGlobalLinks();
        loading = false;
      })
      .catch((error) => {
        console.error("Error:", error);
        loading = false;
      });
  }

  function handleExecute(evaluator: tExecutionEvaluator) {
    console.log("Executing evaluator", $state.snapshot(evaluator));
    executing_evaluator_name = evaluator.name;
    fetch(`${server_address}/primitive_task/evaluators/run/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        evaluator,
        session_id,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("evaluator execution result: ", data);
        executing_evaluator_name = undefined;
        executed_evaluator_name = evaluator.name;
        ask_to_check_results = true;
      })
      .catch((error) => {
        console.error("Error:", error);
        executing_evaluator_name = undefined;
      });
  }
  async function handleToggleExpand(evaluator_name: string) {
    console.log("toggling expand", evaluator_name);
    evaluator_node_expanded = evaluator_node_expanded.includes(evaluator_name)
      ? evaluator_node_expanded.filter((name) => name !== evaluator_name)
      : [...evaluator_node_expanded, evaluator_name];
    await tick();
    update_dag(evaluators);
  }

  function navigate_to_results(node_name: string) {
    console.log("navigating to results: ", node_name);
    const evaluator = evaluators.find((task) => task.name === node_name);
    handleInspectEvaluatorNode(evaluator, true);
  }

  const updateGlobalLinks: Function = getContext("updateGlobalLinks");
  onMount(() => {
    console.log("evaluation nodes mounted,", tasks);
    dag_renderer.init(updateGlobalLinks);
    update_dag(evaluators);
  });
</script>

<div class="flex flex-col gap-y-1 grow">
  <div class="flex flex-col gap-y-1 grow">
    <div
      class="relative bg-emerald-50 w-full flex justify-center z-10"
      class:loading-canvas={loading}
    >
      <span class="text-[1.5rem] text-slate-600 font-semibold italic">
        Evaluation
      </span>
      <div class="absolute right-3 top-0 bottom-0 flex items-center gap-x-2">
        <button
          class="flex items-center justify-center p-0.5 hover:bg-emerald-300 rounded-full outline-2 outline-gray-800"
          title="Add Node"
          onclick={handleAddEvaluator}
        >
          <img src="plus.svg" alt="add" class="w-4 h-4" />
        </button>
      </div>
    </div>

    <div class="relative flex flex-col gap-y-1 grow">
      {#if loading}
        <div
          class="absolute top-0 left-0 right-0 flex items-center justify-center"
        >
          <div class="flex gap-x-2">
            <img
              src="loader_circle.svg"
              class="w-6 h-6 animate-spin opacity-50"
              alt="loading"
            />
            <span class="animate-pulse"
              >Generating for "{generating_for_description}"
            </span>
          </div>
        </div>
      {/if}
      {#if generating_recommendations}
        <div
          class="absolute top-0 left-0 right-0 flex items-center justify-center"
        >
          <div class="flex gap-x-2">
            <img
              src="loader_circle.svg"
              class="w-6 h-6 animate-spin opacity-50"
              alt="loading"
            />
            <span class="animate-pulse">Generating Recommendations..." </span>
          </div>
        </div>
      {/if}
      {#if adding_evaluator}
        <div
          class="absolute top-0 bottom-0 left-0 right-0 bg-emerald-50 z-50 flex justify-center"
        >
          <div
            class="bg-white absolute top-[30%] left-2 right-2 h-fit p-4 outline-2 outline-slate-300 rounded shadow-md"
          >
            <AddExecutionEvaluator
              tasks={tasks
                .filter((t) => t.label !== "Root")
                .filter((t) => t.execution)
                .map((t) => [t.id as string, t.label as string])}
              {handleGenerateEvaluator}
            ></AddExecutionEvaluator>
            <button
              aria-label="close"
              class="absolute right-1 top-0.5"
              onclick={() => (adding_evaluator = false)}
            >
              <svg
                class="w-5 h-5 hover:bg-red-200 rounded-full hover:stroke-black"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="gray"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                ><circle cx="12" cy="12" r="10" /><path d="m15 9-6 6" /><path
                  d="m9 9 6 6"
                /></svg
              >
            </button>
          </div>
        </div>
      {/if}
      <svg id={svgId} class="w-full h-full absolute overflow-visible"></svg>
      <div class="evaluattor-nodes relative w-full flex flex-col-reverse">
        {#each evaluators as evaluator, index}
          <div
            class="evaluator-card-container absolute task-wrapper bg-[#f6fffb] flex flex-col justify-center outline-1 outline-gray-300 rounded-sm shadow transition-all"
            class:executing={executing_evaluator_name === evaluator.name}
            style:z-index={evaluators.length - index}
            data-id={evaluator.name}
          >
            {#if ask_to_check_results && executed_evaluator_name === evaluator.name}
              <div
                class="absolute top-1/2 -translate-y-1/2 right-[calc(100%+2px)] flex justify-center z-20"
              >
                <div
                  class="rounded w-max bg-[#f6faff] outline-0 outline-gray-200 border-t-6 border-emerald-200 shadow-[0px_0px_1px_1px_lightgray] px-2 py-1 flex flex-col gap-y-2 justify-center items-center font-mono gap-x-8"
                >
                  <span class="text-slate-600 font-semibold italic">
                    Execution Complete!
                  </span>
                  <div
                    class="flex justify-between w-full text-sm gap-x-2 italic"
                  >
                    <button
                      class="bg-green-100 outline-2 outline-gray-200 hover:bg-green-200 px-2 py-1 rounded text-slate-600"
                      onclick={() => {
                        ask_to_check_results = false;
                        navigate_to_results(executed_evaluator_name!);
                      }}>Results</button
                    >
                    <button
                      class="bg-red-100 outline-2 outline-gray-200 hover:bg-red-200 px-2 py-1 rounded text-slate-600"
                      onclick={() => {
                        ask_to_check_results = false;
                      }}>Close</button
                    >
                  </div>
                </div>
              </div>
            {/if}

            <ExecutionEvaluatorCard
              bind:evaluator={evaluators[index]}
              expand={evaluator_node_expanded.includes(evaluator.name)}
              handleDeleteEvaluator={() => {
                evaluatorState.evaluators = evaluators.filter(
                  (e) => e !== evaluator
                );
              }}
              {handleExecute}
              handleInspectEvaluator={handleInspectEvaluatorNode}
              handleToggleExpand={() => handleToggleExpand(evaluator.name)}
            ></ExecutionEvaluatorCard>
          </div>
        {/each}
      </div>
      <button
        class="absolute left-2 top-2 bg-emerald-50 font-mono hover:bg-emerald-100 p-1 flex justify-center items-center rounded outline-2 outline-emerald-200 z-10"
        title="Reset Positions"
        tabindex="0"
        onclick={() => dag_renderer.resetTranslate()}
        onkeyup={() => {}}
      >
        <img src="center.svg" class="w-5 h-5" alt="center" />
      </button>
      <button
        class="self-end font-mono text-sm bg-emerald-50 text-slate-700 hover:bg-emerald-100 px-4 py-1 mx-2 w-min flex justify-center rounded outline-2 outline-emerald-200 z-10"
        title="Generate Recommendations"
        tabindex="0"
        onclick={() => handleGenerateRecommendations()}
        onkeyup={() => {}}
      >
        Recommend
      </button>
    </div>
  </div>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .disabled {
    @apply opacity-50 pointer-events-none;
  }
  .loading-canvas {
    position: relative;
    background: linear-gradient(
      90deg,
      #f6fffb 20%,
      #79ffaf 40%,
      #3effc2 60%,
      transparent 80%
    );
    background-size: 200% 200%;
    animation: dash 3s linear infinite;
    border: 4px solid transparent;
  }
  .executing::before {
    content: "";
    position: absolute;
    top: 0;
    right: calc(100% + 3px);
    bottom: 0;
    background-image: url("loader_circle.svg");
    background-size: contain;
    background-repeat: no-repeat;
    z-index: 100;
    @apply w-7 h-7 animate-spin;
  }
  .executing {
    @apply animate-pulse;
  }
</style>
