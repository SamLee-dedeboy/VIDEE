<script lang="ts">
  import { server_address } from "constants";
  import { onMount, tick } from "svelte";
  import type { tSemanticTask, tNode } from "types";
  import { DAG } from "renderer/dag";
  import * as d3 from "d3";
  import { getContext } from "svelte";
  import SimpleSemanticTaskCard from "./SimpleSemanticTaskCard.svelte";
  import { semanticTaskPlanState } from "../ExecutionStates.svelte";
  let {
    decomposing_goal,
    handleConvert,
  }: {
    decomposing_goal: boolean;
    handleConvert: Function;
  } = $props();
  const semantic_tasks: tSemanticTask[] = $derived(
    semanticTaskPlanState.semantic_tasks
  );
  const session_id = (getContext("session_id") as Function)();
  /**
   * Stores the id of the expanded tasks
   */
  let semantic_tasks_show_sub_tasks: string[] = $state([]);
  /**
   * Stores the flattened semantic tasks
   */
  let semantic_tasks_flattened: tSemanticTask[] = $derived(
    flatten(semantic_tasks, semantic_tasks_show_sub_tasks)
  );
  let task_card_expanded: string[] = $state([]);
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "plan-dag-svg";
  const node_size: [number, number] = [500, 250];
  let dag_renderer = new DAG(
    svgId,
    node_size,
    ".semantic-task-card-container",
    ".semantic-tasks"
  );

  $effect(() => {
    update_dag(semantic_tasks_flattened);
  });

  export function rerender_plan() {
    update_dag(semantic_tasks_flattened);
  }
  /**
   * Flatten the semantic tasks
   * @param _semantic_tasks
   */
  function flatten(
    _semantic_tasks: tSemanticTask[] | undefined,
    _semantic_tasks_show_sub_tasks: string[]
  ) {
    console.log({ _semantic_tasks, _semantic_tasks_show_sub_tasks });
    // flatten the semantic tasks with bfs
    if (!_semantic_tasks) return [];
    const queue = [..._semantic_tasks];
    const flattened: tSemanticTask[] = [];
    while (queue.length) {
      let task = queue.shift()!;
      if (task.label === "END") continue;
      if (task.label === "Root") continue;
      flattened.push(task);
      if (task?.sub_tasks && _semantic_tasks_show_sub_tasks.includes(task.id)) {
        queue.push(...task.sub_tasks);
      }
    }

    console.log({ flattened });
    return flattened;
  }

  /**
   * Prepare the data for the dag renderer
   * by adding the bounding box of each task card
   * @param _semantic_tasks_flattened
   */
  async function update_dag(_semantic_tasks_flattened: tSemanticTask[]) {
    console.log("updating semantic dag:", _semantic_tasks_flattened);
    // get the bounding box of each task card
    const semantic_task_divs: NodeListOf<HTMLElement> =
      document.querySelectorAll(".semantic-task-card-container");
    const dag_data: tNode[] = Array.from(semantic_task_divs).map((div) => {
      const id = (div as HTMLElement).dataset.id || "";
      const node_data: tSemanticTask = _semantic_tasks_flattened.find(
        (task) => task.id === id
      )!;
      const transform_scale =
        div.style.transform === ""
          ? 1
          : d3.zoomTransform(d3.select(`#${svgId}`).node()).k;
      return {
        id: node_data.id,
        parentIds: node_data.parentIds,
        data: node_data,
        bbox: {
          ...div.getBoundingClientRect(),
          width: div.getBoundingClientRect().width / transform_scale,
          height: div.getBoundingClientRect().height / transform_scale,
        },
      };
    });

    // call renderer
    dag_renderer.update(dag_data, undefined, undefined, false);
  }

  // UI handlers
  function handleToggleShowSubTasks(task_id: string) {
    semantic_tasks_show_sub_tasks = semantic_tasks_show_sub_tasks.includes(
      task_id
    )
      ? semantic_tasks_show_sub_tasks.filter((id) => id !== task_id)
      : [...semantic_tasks_show_sub_tasks, task_id];
  }

  // handlers with server-side updates
  function handleAddTask() {
    semanticTaskPlanState.addTask();
  }

  function handleDeleteTask(task: tSemanticTask) {
    semanticTaskPlanState.deleteTask(task);
  }

  function handleDeleteSubTasks(task: tSemanticTask) {
    console.log({ task, semantic_tasks });
  }

  function handleDecompose(task: tSemanticTask) {
    fetch(`${server_address}/semantic_task/task_decomposition/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ task, current_steps: semantic_tasks }),
    })
      .then((response) => response.json())
      .then((data) => {
        semanticTaskPlanState.semantic_tasks = data;
        console.log("task decomposed: ", { data });
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  async function handleToggleExpand(task_id: string) {
    task_card_expanded = task_card_expanded.includes(task_id)
      ? task_card_expanded.filter((id) => id !== task_id)
      : [...task_card_expanded, task_id];

    // trigger re-render
    await tick();
    update_dag(semantic_tasks_flattened);
  }

  const updateGlobalLinks: Function = getContext("updateGlobalLinks");
  onMount(() => {
    console.log("Semantic Tasks init");
    dag_renderer.init(updateGlobalLinks);
    update_dag(semantic_tasks);
  });
</script>

<div class="flex flex-col gap-y-1 grow">
  <div class="relative bg-orange-100 w-full flex justify-center z-10">
    <span
      class="canvas-header text-[1.5rem] text-slate-600 font-semibold italic"
    >
      Plan
    </span>
    <div class="absolute right-3 top-0 bottom-0 flex items-center gap-x-2">
      <button
        class="flex items-center justify-center p-0.5 hover:bg-orange-300 rounded-full outline-2 outline-gray-800"
        title="Add Node"
        onclick={handleAddTask}
      >
        <img src="plus.svg" alt="add" class="w-4 h-4" />
      </button>
    </div>
  </div>

  <!-- style:height={Math.max(
      semantic_tasks_flattened.length * 2 * node_size[1] * 1.5,
      1000
    ) + "px"} -->
  <div class="relative flex flex-col gap-y-1 grow">
    {#if decomposing_goal}
      <div
        class="absolute top-0 left-0 right-0 flex items-center justify-center"
      >
        <div class="flex gap-x-2">
          <img
            src="loader_circle.svg"
            class="w-6 h-6 animate-spin opacity-50"
            alt="loading"
          />
          <span class="animate-pulse">Decomposing...</span>
        </div>
      </div>
    {/if}
    <svg id={svgId} class="w-full h-full absolute overflow-visible"></svg>
    <div class="semantic-tasks relative w-full flex flex-col-reverse">
      {#each semantic_tasks_flattened as task, index}
        <div
          class="semantic-task-card-container absolute flex task-wrapper bg-[#FFCFB1] outline-1 outline-gray-300 rounded-sm shadow transition-all duration-500"
          data-id={task.id}
        >
          <SimpleSemanticTaskCard
            {task}
            task_options={semantic_tasks
              .filter(
                (t) =>
                  t.id !== task.id &&
                  !task.parentIds.includes(t.id) &&
                  !task.children.includes(t.id)
              )
              .map((task) => [task.id, task.label])}
            expand={task_card_expanded.includes(task.id)}
            {handleDecompose}
            {handleDeleteSubTasks}
            {handleToggleShowSubTasks}
            {handleDeleteTask}
            handleToggleExpand={() => handleToggleExpand(task.id)}
            handleAddParent={(parent_id) =>
              semanticTaskPlanState.addParent(task, parent_id)}
          ></SimpleSemanticTaskCard>
        </div>
      {/each}
    </div>
    {#if semantic_tasks_flattened.length > 0}
      <button
        class="self-end font-mono text-sm bg-orange-50 text-slate-700 hover:bg-orange-100 px-4 py-1 mx-2 w-min flex justify-center rounded outline-2 outline-orange-200 z-10"
        tabindex="0"
        onclick={() => handleConvert()}
        onkeyup={() => {}}
      >
        Convert
      </button>
    {/if}
    <button
      class="absolute left-2 top-2 bg-orange-50 font-mono hover:bg-orange-100 p-1 flex justify-center items-center rounded outline-2 outline-orange-200 z-10"
      title="Reset Positions"
      tabindex="0"
      onclick={() => dag_renderer.resetTranslate()}
      onkeyup={() => {}}
    >
      <img src="center.svg" class="w-5 h-5" alt="center" />
    </button>
  </div>
</div>

<style lang="postcss">
</style>
