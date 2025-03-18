<script lang="ts">
  import type {
    tSemanticTask,
    tPrimitiveTask,
    tExecutionEvaluator,
  } from "types";
  import * as d3 from "d3";
  import { getContext, setContext, tick } from "svelte";
  import { server_address } from "constants";
  import PrimitiveTasks from "./PrimitiveTasks.svelte";
  import SemanticTaskPlan from "../Plan/SemanticTaskPlan.svelte";
  import EvaluationNodes from "../Evaluation/EvaluationNodes.svelte";
  import {
    evaluatorState,
    primitiveTaskState,
    semanticTaskPlanState,
  } from "../ExecutionStates.svelte";
  let {
    user_goal,
    // plans
    decomposing_goal,
    handleConvert,

    // execution
    converting,
    compiling,
    handleInspectPrimitiveTask = () => {},

    // evaluation
    // evaluators = $bindable([]),
    handleInspectEvaluatorNode = () => {},
  }: {
    user_goal: string;
    decomposing_goal: boolean;
    handleConvert: Function;

    converting: boolean;
    compiling: boolean;
    handleInspectPrimitiveTask: Function;

    // evaluators: tExecutionEvaluator[];
    handleInspectEvaluatorNode: Function;
  } = $props();
  const svgId = "controller-dag-svg";
  let controllers = $state({
    show_plan: true,
    show_execution: true,
    show_evaluation: false,
  });

  const session_id = (getContext("session_id") as Function)();
  let generating_recommendations = $state(false);
  const semantic_tasks = $derived(semanticTaskPlanState.semantic_tasks);
  const evaluators = $derived(evaluatorState.evaluators);
  const primitive_tasks = $derived(primitiveTaskState.primitiveTasks);

  let plan_component: any = $state();
  let execution_component: any = $state();
  let evaluation_component: any = $state();

  async function rerender_all() {
    await tick();
    console.log("Rerendering all");
    plan_component?.rerender_plan();
    execution_component?.rerender_execution();
    evaluation_component?.rerender_evaluation();
    updateLinks(semantic_tasks, primitive_tasks, evaluators);
  }

  async function updateLinks(
    _semantic_tasks: tSemanticTask[],
    _primitive_tasks: tPrimitiveTask[],
    _evaluator_nodes: tExecutionEvaluator[]
  ) {
    // console.log(
    //   "Updating links",
    //   _semantic_tasks,
    //   _primitive_tasks,
    //   _evaluator_nodes
    // );
    await tick();
    const svg = d3.select(`#${svgId}`);
    // links between plan and execution
    if (controllers.show_plan && controllers.show_execution) {
      let plan_execution_links: any[] = [];
      _primitive_tasks.forEach((primitive_task) => {
        if (primitive_task.id === "-1") return;
        const solves = primitive_task.solves;
        if (!semantic_tasks.find((task) => task.id === solves)) return;
        const source = document.querySelector(
          `.semantic-task-card-container[data-id="${solves}"]`
        );
        const target = document.querySelector(
          `.primitive-task-card-container[data-id="${primitive_task.id}"]`
        );
        const source_bbox = getBboxRelativeToCanvas(source);
        const target_bbox = getBboxRelativeToCanvas(target);
        plan_execution_links.push({
          source: {
            x: source_bbox.left + source_bbox.width / 2,
            y: source_bbox.top + source_bbox.height / 2,
          },
          target: {
            x: target_bbox.left + target_bbox.width / 2,
            y: target_bbox.top + target_bbox.height / 2,
          },
        });
      });
      svg
        .select("g.plan-execution")
        .selectAll("line.links")
        .data(plan_execution_links)
        .join("line")
        .attr("class", "links")
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y)
        .attr("stroke", "black")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "5,5");
    } else {
      svg.select("g.plan-execution").selectAll("line.links").remove();
    }
    // links between execution and evaluation
    if (controllers.show_execution && controllers.show_evaluation) {
      let execution_evaluation_links: any[] = [];
      _evaluator_nodes.forEach((evaluator_node) => {
        if (!evaluator_node.isRoot) return;
        const target_task = evaluator_node.task;
        if (!primitive_tasks.find((task) => task.id === target_task)) return;
        const source = document.querySelector(
          `.primitive-task-card-container[data-id="${target_task}"]`
        );
        const target = document.querySelector(
          `.evaluator-card-container[data-id="${evaluator_node.name}"]`
        );
        const source_bbox = getBboxRelativeToCanvas(source);
        const target_bbox = getBboxRelativeToCanvas(target);
        execution_evaluation_links.push({
          source: {
            x: source_bbox.left + source_bbox.width / 2,
            y: source_bbox.top + source_bbox.height / 2,
          },
          target: {
            x: target_bbox.left + target_bbox.width / 2,
            y: target_bbox.top + target_bbox.height / 2,
          },
        });
      });
      svg
        .select("g.execution-evaluation")
        .selectAll("line.links")
        .data(execution_evaluation_links)
        .join("line")
        .attr("class", "links")
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y)
        .attr("stroke", "black")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "5,5");
    } else {
      svg.select("g.execution-evaluation").selectAll("line.links").remove();
    }
  }
  setContext("updateGlobalLinks", () =>
    updateLinks(semantic_tasks, primitive_tasks, evaluators)
  );

  function getBboxRelativeToCanvas(element) {
    const canvas = document.querySelector(".whole-canvas")!;
    const elementRect = element.getBoundingClientRect();
    const canvasRect = canvas?.getBoundingClientRect();

    return {
      top: elementRect.top - canvasRect.top,
      left: elementRect.left - canvasRect.left,
      width: elementRect.width,
      height: elementRect.height,
    };
  }

  export function generate_evaluator_recommendations(
    primitive_tasks: tPrimitiveTask[]
  ) {
    console.log("Generating recommendations");
    generating_recommendations = true;
    fetch(`${server_address}/primitive_task/evaluators/recommend/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tasks: primitive_tasks.filter((task) => task.id !== "-1"),
        session_id,
        goal: user_goal,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Recommendations:", data);
        const user_defined_evaluators = evaluators.filter(
          (evaluator) => evaluator.recommendation === false
        );
        evaluatorState.evaluators = [
          ...user_defined_evaluators,
          ...data["result"],
        ];
        generating_recommendations = false;
        evaluation_component.rerender_evaluation();
      })
      .catch((error) => {
        console.error("Error:", error);
        generating_recommendations = false;
      });
  }
</script>

<div class="flex grow bg-gray-50">
  <div class="whole-canvas absolute left-0 right-0 top-[36px] bottom-0">
    <svg id={svgId} class="w-full h-full">
      <g class="plan-execution"></g>
      <g class="execution-evaluation"></g>
    </svg>
  </div>
  <div class="divide-x divide-gray-400 divide-dashed flex grow">
    {#if controllers.show_plan}
      <div class="plane flex-1 flex relative z-10">
        <SemanticTaskPlan
          bind:this={plan_component}
          {decomposing_goal}
          {handleConvert}
        ></SemanticTaskPlan>
        <button
          class="absolute left-1 top-1 z-20 hover:bg-orange-300 rounded"
          title="Hide Panel"
          onclick={() => {
            controllers.show_plan = false;
            rerender_all();
          }}><img src="square-minus.svg" class="w-5 h-5" alt="hide" /></button
        >
      </div>
    {:else}
      <div class="px-2 bg-orange-100 flex h-fit hover:bg-orange-200">
        <button
          class="z-20 flex text-[1.5rem] text-slate-600 font-semibold italic"
          title="Show Panel"
          onclick={() => {
            controllers.show_plan = true;
            rerender_all();
          }}>Plan</button
        >
      </div>
    {/if}
    {#if controllers.show_execution}
      <div class="plane flex-1 flex relative">
        <PrimitiveTasks
          bind:this={execution_component}
          {converting}
          {compiling}
          {handleInspectPrimitiveTask}
        ></PrimitiveTasks>
        <button
          class="absolute left-1 top-1 z-20 hover:bg-blue-200 rounded"
          title="Hide Panel"
          onclick={() => {
            controllers.show_execution = false;
            rerender_all();
          }}><img src="square-minus.svg" class="w-5 h-5" alt="hide" /></button
        >
      </div>
    {:else}
      <div class="px-2 bg-[#f2f8fd] flex h-fit hover:bg-blue-200">
        <button
          class="z-20 flex text-[1.5rem] text-slate-600 font-semibold italic"
          title="Show Panel"
          onclick={() => {
            controllers.show_execution = true;
            rerender_all();
          }}>Execution</button
        >
      </div>
    {/if}
    {#if controllers.show_evaluation}
      <div class="plane flex-1 flex relative">
        <EvaluationNodes
          {generating_recommendations}
          handleGenerateRecommendations={() =>
            generate_evaluator_recommendations(primitive_tasks)}
          bind:this={evaluation_component}
          tasks={primitive_tasks}
          {handleInspectEvaluatorNode}
        ></EvaluationNodes>
        <button
          class="absolute left-1 top-1 z-20 hover:bg-emerald-200 rounded"
          title="Hide Panel"
          onclick={() => {
            controllers.show_evaluation = false;
            rerender_all();
          }}><img src="square-minus.svg" class="w-5 h-5" alt="hide" /></button
        >
      </div>
    {:else}
      <div
        class="px-2 bg-emerald-50 flex h-fit hover:bg-emerald-200"
        class:disabled={compiling || converting || primitive_tasks.length === 0}
      >
        <button
          class="z-20 flex text-[1.5rem] text-slate-600 font-semibold italic"
          title="Show Panel"
          onclick={() => {
            controllers.show_evaluation = true;
            rerender_all();
          }}>Evaluation</button
        >
      </div>
    {/if}
  </div>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .plane {
  }
  .disabled {
    pointer-events: none;
    opacity: 0.5;
  }
</style>
