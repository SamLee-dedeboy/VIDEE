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
  let semantic_tasks_show_children: string[] = $state([]);
  /**
   * Stores the flattened semantic tasks
   */
  let semantic_tasks_flattened: tSemanticTask[] = $derived(
    flatten(semantic_tasks, semantic_tasks_show_children)
  );
  let task_card_expanded: string[] = $state([]);
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "dag-svg";
  const node_size: [number, number] = [150, 100];
  let dag_renderer = new DAG(
    svgId,
    node_size,
    ".semantic-task-card-container",
    ".semantic-tasks"
  );

  $effect(() => {
    update_dag(semantic_tasks_flattened);
  });

  /**
   * Flatten the semantic tasks
   * @param _semantic_tasks
   */
  function flatten(
    _semantic_tasks: tSemanticTask[] | undefined,
    _semantic_tasks_show_children: string[]
  ) {
    console.log({ _semantic_tasks });
    // flatten the semantic tasks with bfs
    if (!_semantic_tasks) return [];
    const queue = [..._semantic_tasks];
    const flattened: tSemanticTask[] = [];
    while (queue.length) {
      let task = queue.shift()!;
      flattened.push(task);
      if (task?.children && _semantic_tasks_show_children.includes(task.id)) {
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
  async function update_dag(_semantic_tasks_flattened: tSemanticTask[]) {
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
    dag_renderer.update(dag_data, semantic_tasks_show_children);
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
        console.log("task decomposed: ", { data });
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

  function handleToggleShowChildren(task_id: string) {
    semantic_tasks_show_children = semantic_tasks_show_children.includes(
      task_id
    )
      ? semantic_tasks_show_children.filter((id) => id !== task_id)
      : [...semantic_tasks_show_children, task_id];
  }

  function handleToggleExpand(task_id: string) {
    task_card_expanded = task_card_expanded.includes(task_id)
      ? task_card_expanded.filter((id) => id !== task_id)
      : [...task_card_expanded, task_id];
  }
  onMount(() => {
    dag_renderer.init();
    update_dag(semantic_tasks);
  });
</script>

<div class="flex flex-col gap-y-1 grow h-fit">
  <span
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-[#FFCFB1] w-full flex justify-center z-10"
    >Semantic Tasks</span
  >
  <!-- style:height={Math.max(
      semantic_tasks_flattened.length * 2 * node_size[1] * 1.5,
      1000
    ) + "px"} -->
  <div class="relative bg-gray-50 flex flex-col gap-y-1 h-[1000px]">
    <svg id={svgId} class="w-full h-full absolute"></svg>
    <div class="semantic-tasks relative w-full">
      {#each semantic_tasks_flattened as task, index}
        <!-- use:draggable={dag_renderer} -->
        <div
          class="semantic-task-card-container absolute flex task-wrapper bg-[#FFCFB1] outline outline-1 outline-gray-300 rounded-sm shadow"
          style:z-index={semantic_tasks_flattened.length - index}
          data-id={task.id}
        >
          <SemanticTaskCard
            {task}
            expand={task_card_expanded.includes(task.id)}
            {handleDecompose}
            {handleDeleteChildren}
            {handleToggleShowChildren}
            handleToggleExpand={() => handleToggleExpand(task.id)}
          ></SemanticTaskCard>
          {#if !task_card_expanded.includes(task.id)}
            <button
              class="flex p-0.5 hover:bg-orange-400 justify-center"
              onclick={() =>
                (task_card_expanded = [...task_card_expanded, task.id])}
            >
              <img
                src="chevron_right.svg"
                class="mt-0.5 w-5 h-4 pointer-events-none"
                alt="handle"
              />
            </button>
          {/if}
        </div>
      {/each}
    </div>
    {#if semantic_tasks_flattened.length > 0}
      <div
        class="self-end py-1 mx-2 bg-gray-100 min-w-[10rem] w-min flex justify-center rounded outline outline-gray-200 z-10"
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
