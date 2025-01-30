<script lang="ts">
  import { server_address } from "constants";
  import { onMount, tick } from "svelte";
  import type {
    tElementaryTaskDescription,
    tElementaryTaskExecution,
    tExecutionState,
    tNode,
    tTask,
  } from "types";
  import { DAG } from "renderer/dag";
  import ElementaryTaskCard from "./ElementaryTaskCard.svelte";
  import { fly, fade, blur } from "svelte/transition";
  import { draggable } from "./draggable";
  import { getContext } from "svelte";
  let {
    elementary_tasks,
  }: {
    elementary_tasks: (tElementaryTaskDescription &
      Partial<tElementaryTaskExecution>)[];
  } = $props();
  let execution_states: Record<string, tExecutionState> | undefined =
    $state(undefined);
  const session_id = (getContext("session_id") as Function)();
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "dag-svg";
  const node_size: [number, number] = [150, 80];
  let dag_renderer = new DAG(svgId, node_size);

  $effect(() => {
    update_dag(elementary_tasks);
  });

  /**
   * Prepare the data for the dag renderer
   * by adding the bounding box of each task card
   * @param _elementary_tasks
   */
  function update_dag(_elementary_tasks: tElementaryTaskDescription[]) {
    console.log("updating elementary dag:", _elementary_tasks);
    // get the bounding box of each task card
    const elementary_task_divs = document.querySelectorAll(
      ".elementary-task-card-container"
    );
    const dag_data: tNode[] = Array.from(elementary_task_divs).map((div) => {
      const id = (div as HTMLElement).dataset.id;
      const node_data: tElementaryTaskDescription = _elementary_tasks.find(
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

  function handleCompile() {
    console.log("Compiling...", { elementary_tasks, session_id });
    fetch(`${server_address}/elementary_task/compile/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ elementary_tasks, session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        elementary_tasks = data.elementary_tasks;
        execution_states = data.execution_state;
        console.log({ data });
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function handleExecute(
    execute_node: tElementaryTaskDescription & tElementaryTaskExecution
  ) {
    console.log("Executing...", { execute_node, session_id });
    fetch(`${server_address}/elementary_task/execute/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ execute_node, session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        execution_states = data.execution_state;
        console.log("execution: ", data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  onMount(() => {
    dag_renderer.init();
    update_dag(elementary_tasks);
    console.log({ execution_states });
  });
</script>

<div class="flex flex-col gap-y-1 grow h-fit">
  <span
    class="text-[1.5rem] text-slate-500 font-semibold italic bg-[#f2f8fd] w-full flex justify-center"
    >Elementary Tasks</span
  >

  <div
    class="relative grow shrink-0 bg-gray-50 px-2"
    style:height={Math.max(
      elementary_tasks.length * 2 * node_size[1] * 1.5,
      800
    ) + "px"}
  >
    <div
      class="py-1 px-2 bg-gray-100 min-w-[10rem] w-min flex justify-center mt-2 rounded outline outline-gray-200"
      tabindex="0"
      role="button"
      onclick={() => handleCompile()}
      onkeyup={() => {}}
    >
      Compile Graph
    </div>
    <svg id={svgId} class="w-full h-full absolute"></svg>
    <div class="elementary-tasks relative w-full flex flex-col-reverse">
      {#each elementary_tasks as task, index}
        <div
          class="elementary-task-card-container absolute task-wrapper -translate-x-1/2 -translate-y-1/2 bg-blue-200 flex gap-x-1 outline outline-1 outline-gray-300 rounded-sm shadow"
          use:draggable={dag_renderer}
          style:z-index={elementary_tasks.length - index}
          data-id={task.id}
        >
          <img
            src="handle.svg"
            class="mt-0.5 w-4 h-4 pointer-events-none"
            alt="handle"
          />
          <ElementaryTaskCard
            {task}
            executable={execution_states?.[task.id].executable || false}
            {handleExecute}
          ></ElementaryTaskCard>
        </div>
      {/each}
    </div>
  </div>
</div>

<style lang="postcss">
</style>
