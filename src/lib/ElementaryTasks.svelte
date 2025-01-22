<script lang="ts">
  import { server_address } from "constants";
  import { onMount, tick } from "svelte";
  import type { tElementaryTask, tNode } from "types";
  import { DAG } from "renderer/dag";
  import ElementaryTaskCard from "./ElementaryTaskCard.svelte";
  import { fly, fade, blur } from "svelte/transition";
  let { elementary_tasks }: { elementary_tasks: tElementaryTask[] } = $props();
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "dag-svg";
  const node_radius = 100;
  let dag_renderer = new DAG(svgId, node_radius);

  $effect(() => {
    update_dag(elementary_tasks);
  });

  /**
   * Prepare the data for the dag renderer
   * by adding the bounding box of each task card
   * @param _elementary_tasks
   */
  function update_dag(_elementary_tasks: tElementaryTask[]) {
    console.log("updating elementary dag:", _elementary_tasks);
    // get the bounding box of each task card
    const semantic_task_divs = document.querySelectorAll(
      ".elementary-task-card-container"
    );
    const dag_data: tNode[] = Array.from(semantic_task_divs).map((div) => {
      const id = (div as HTMLElement).dataset.id;
      const node_data: tElementaryTask = _elementary_tasks.find(
        (task) => task.id === id
      )!;
      return {
        ...node_data,
        bbox: div.getBoundingClientRect(),
      };
    });

    // call renderer
    dag_renderer.update(dag_data, [], ".elementary-task-card-container");
  }

  onMount(() => {
    dag_renderer.init();
    update_dag(elementary_tasks);
  });
</script>

<div
  class="relative mt-[2rem] shrink-0"
  style:height={Math.min(elementary_tasks.length * 2 * node_radius, 10000) +
    "px"}
>
  <span>Elementary Tasks</span>
  <svg id={svgId} class="w-full h-full absolute"></svg>
  <div class="elementary-tasks relative w-full flex flex-col-reverse">
    {#each elementary_tasks as task, index}
      <div
        class="elementary-task-card-container absolute task-wrapper -translate-x-1/2 -translate-y-1/2"
        style:z-index={elementary_tasks.length - index}
        data-id={task.id}
      >
        <ElementaryTaskCard {task}></ElementaryTaskCard>
      </div>
    {/each}
  </div>
</div>

<style lang="postcss">
</style>
