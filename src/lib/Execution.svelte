<script lang="ts">
  import type {
    tSemanticTask,
    tNode,
    tPrimitiveTask,
    tExecutionEvaluator,
    tExecutionState,
    tTask,
  } from "types";
  import { DAG } from "renderer/dag";
  import { slide } from "svelte/transition";
  import * as d3 from "d3";
  import { getContext, setContext, tick } from "svelte";
  import PrimitiveTasks from "./PrimitiveTasks.svelte";
  import SemanticTaskPlan from "./SemanticTaskPlan.svelte";
  import EvaluationNodes from "./EvaluationNodes.svelte";
  import {
    evaluatorState,
    primitiveTaskState,
    semanticTaskPlanState,
  } from "./ExecutionStates.svelte";
  let {
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
    decomposing_goal: boolean;
    handleConvert: Function;

    converting: boolean;
    compiling: boolean;
    handleInspectPrimitiveTask: Function;

    // evaluators: tExecutionEvaluator[];
    handleInspectEvaluatorNode: Function;
  } = $props();
  const session_id = (getContext("session_id") as Function)();
  const svgId = "controller-dag-svg";
  let controllers = $state({
    show_plan: true,
    show_execution: true,
    show_evaluation: false,
  });

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
    await tick();
    const svg = d3.select(`#${svgId}`);
    // links between plan and execution
    if (controllers.show_plan && controllers.show_execution) {
      let plan_execution_links: any[] = [];
      _primitive_tasks.forEach((primitive_task) => {
        const solves = primitive_task.solves;
        if (!semantic_tasks.find((task) => task.id === solves)) return;
        const source = document.querySelector(`[data-id="${solves}"]`);
        const target = document.querySelector(
          `[data-id="${primitive_task.id}"]`
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
        const target_task = evaluator_node.task;
        if (!primitive_tasks.find((task) => task.id === target_task)) return;
        const source = document.querySelector(`[data-id="${target_task}"]`);
        const target = document.querySelector(
          `[data-id="${evaluator_node.name}"]`
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
          bind:this={evaluation_component}
          tasks={primitive_tasks}
          {handleInspectEvaluatorNode}
        ></EvaluationNodes>
        <button
          class="absolute left-1 top-1 z-20 hover:bg-emerald-200 rounded"
          onclick={() => {
            controllers.show_evaluation = false;
            rerender_all();
          }}><img src="square-minus.svg" class="w-5 h-5" alt="hide" /></button
        >
      </div>
    {:else}
      <div
        class="px-2 bg-emerald-50 flex h-fit hover:bg-emerald-200"
        class:disabled={compiling || converting}
      >
        <button
          class="z-20 flex text-[1.5rem] text-slate-600 font-semibold italic"
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
  @reference "../app.css";
  .plane {
  }
  .disabled {
    pointer-events: none;
    opacity: 0.5;
  }
</style>
