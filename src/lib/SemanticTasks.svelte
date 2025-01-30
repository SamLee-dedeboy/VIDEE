<script lang="ts">
  import { server_address } from "constants";
  import { onMount, tick } from "svelte";
  import type { tSemanticTask, tNode } from "types";
  import { DAG } from "renderer/dag";
  import SemanticTaskCard from "./SemanticTaskCard.svelte";
  import { fly, fade, blur } from "svelte/transition";
  import { draggable } from "./draggable";
  let {
    semantic_tasks,
    handleConvert,
  }: { semantic_tasks: tSemanticTask[]; handleConvert: Function } = $props();
  /**
   * Stores the id of the expanded tasks
   */
  let semantic_tasks_expanded: string[] = $state([]);
  /**
   * Stores the flattened semantic tasks
   */
  let semantic_tasks_flattened: tSemanticTask[] = $derived(
    flatten(semantic_tasks, semantic_tasks_expanded)
  );
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "dag-svg";
  const node_size: [number, number] = [150, 100];
  let dag_renderer = new DAG(svgId, node_size);

  $effect(() => {
    update_dag(semantic_tasks_flattened);
  });

  /**
   * Flatten the semantic tasks
   * @param _semantic_tasks
   */
  function flatten(
    _semantic_tasks: tSemanticTask[] | undefined,
    _semantic_tasks_expanded: string[]
  ) {
    console.log({ _semantic_tasks });
    // flatten the semantic tasks with bfs
    if (!_semantic_tasks) return [];
    const queue = [..._semantic_tasks];
    const flattened: tSemanticTask[] = [];
    while (queue.length) {
      let task = queue.shift()!;
      flattened.push(task);
      if (task?.children && _semantic_tasks_expanded.includes(task.id)) {
        queue.push(...task.children);
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
  function update_dag(_semantic_tasks_flattened: tSemanticTask[]) {
    console.log("updating semantic dag:", _semantic_tasks_flattened);
    // get the bounding box of each task card
    const semantic_task_divs = document.querySelectorAll(
      ".semantic-task-card-container"
    );
    const dag_data: tNode[] = Array.from(semantic_task_divs).map((div) => {
      const id = (div as HTMLElement).dataset.id || "";
      const node_data: tSemanticTask = _semantic_tasks_flattened.find(
        (task) => task.id === id
      )!;
      return {
        ...node_data,
        bbox: div.getBoundingClientRect(),
      };
    });

    // call renderer
    dag_renderer.update(
      dag_data,
      semantic_tasks_expanded,
      ".semantic-task-card-container"
    );
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
        semantic_tasks = data;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function handleDeleteChildren(task: tSemanticTask) {
    console.log({ task, semantic_tasks });
    fetch(`${server_address}/semantic_task/delete_children/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ task, current_steps: semantic_tasks }),
    })
      .then((response) => response.json())
      .then((data) => {
        semantic_tasks = data;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  onMount(() => {
    dag_renderer.init();
    update_dag(semantic_tasks);
  });
</script>

<div class="flex flex-col gap-y-1 grow h-fit">
  <span
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-[#FFCFB1] w-full flex justify-center"
    >Semantic Tasks</span
  >
  <div
    class="relative bg-gray-50 flex flex-col gap-y-1"
    style:height={Math.max(
      semantic_tasks_flattened.length * 2 * node_size[1] * 1.5,
      1000
    ) + "px"}
  >
    <svg id={svgId} class="w-full h-full absolute"></svg>
    <div class="semantic-tasks relative w-full">
      {#each semantic_tasks_flattened as task, index}
        <div
          use:draggable={dag_renderer}
          class="semantic-task-card-container absolute task-wrapper -translate-x-1/2 -translate-y-1/2 bg-[#FFCFB1] flex gap-x-1 outline outline-1 outline-gray-300 rounded-sm shadow"
          style:z-index={semantic_tasks_flattened.length - index}
          data-id={task.id}
        >
          <img
            src="handle.svg"
            class="mt-0.5 w-4 h-4 pointer-events-none"
            alt="handle"
          />
          <SemanticTaskCard
            {task}
            {handleDecompose}
            {handleDeleteChildren}
            handleToggle={() => {
              semantic_tasks_expanded = semantic_tasks_expanded.includes(
                task.id
              )
                ? semantic_tasks_expanded.filter((id) => id !== task.id)
                : [...semantic_tasks_expanded, task.id];
            }}
          ></SemanticTaskCard>
        </div>
      {/each}
    </div>
    {#if semantic_tasks_flattened.length > 0}
      <div
        class="py-1 mx-2 bg-gray-100 min-w-[10rem] w-min flex justify-center rounded outline outline-gray-200 z-10"
        tabindex="0"
        role="button"
        onclick={() => handleConvert()}
        onkeyup={() => {}}
      >
        Convert
      </div>
    {/if}
  </div>
</div>

<style lang="postcss">
</style>
