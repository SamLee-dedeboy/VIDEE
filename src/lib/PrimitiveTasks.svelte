<script lang="ts">
  import { server_address } from "constants";
  import { onMount, setContext, tick } from "svelte";
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
    tExecutionState,
    tNode,
    tTask,
    tPrimitiveTask,
  } from "types";
  import * as d3 from "d3";
  import { DAG } from "renderer/dag";
  import PrimitiveTaskCard from "./PrimitiveTaskCard.svelte";
  import { fly, fade, blur } from "svelte/transition";
  import { draggable } from "./draggable";
  import { getContext } from "svelte";
  import {
    primitiveTaskState,
    primitiveTaskExecutionStates,
  } from "./ExecutionStates.svelte";
  let {
    converting,
    compiling,
    handleInspectPrimitiveTask = () => {},
  }: {
    converting: boolean;
    compiling: boolean;
    handleInspectPrimitiveTask: Function;
  } = $props();
  const primitive_tasks = $derived(
    primitiveTaskState.primitiveTasks
  ) as tPrimitiveTaskDescription[];
  let task_card_expanded: string[] = $state([]);
  const session_id = (getContext("session_id") as Function)();
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "execution-dag-svg";
  const node_size: [number, number] = [150, 80];
  let dag_renderer = new DAG(
    svgId,
    node_size,
    ".primitive-task-card-container",
    ".primitive-tasks"
  );

  $effect(() => {
    update_dag(primitive_tasks);
  });

  export function rerender_execution() {
    update_dag(primitive_tasks);
  }

  /**
   * Prepare the data for the dag renderer
   * by adding the bounding box of each task card
   * @param _primitive_tasks
   */
  function update_dag(_primitive_tasks: tPrimitiveTaskDescription[]) {
    console.log("updating primitive dag:", _primitive_tasks);
    // get the bounding box of each task card
    const primitive_task_divs: NodeListOf<HTMLElement> =
      document.querySelectorAll(".primitive-task-card-container");
    const dag_data: tNode[] = Array.from(primitive_task_divs).map((div) => {
      const id = (div as HTMLElement).dataset.id;
      const node_data: tPrimitiveTaskDescription = _primitive_tasks.find(
        (task) => task.id === id
      )!;
      const transform_scale =
        div.style.transform === ""
          ? 1
          : d3.zoomTransform(d3.select(`#${svgId}`).node()).k;
      return {
        ...node_data,
        data: node_data,
        bbox: {
          ...div.getBoundingClientRect(),
          width: div.getBoundingClientRect().width / transform_scale,
          height: div.getBoundingClientRect().height / transform_scale,
        },
      };
    });
    // call renderer
    dag_renderer.update(dag_data, []);
  }

  // UI handlers
  async function handleToggleExpand(task_id: string) {
    task_card_expanded = task_card_expanded.includes(task_id)
      ? task_card_expanded.filter((id) => id !== task_id)
      : [...task_card_expanded, task_id];
    await tick();
    update_dag(primitive_tasks);
  }

  // handlers with server-side updates
  // function handleCompile() {
  //   console.log("Compiling...", { primitive_tasks, session_id });
  //   compiling = true;
  //   fetch(`${server_address}/primitive_task/compile/`, {
  //     method: "POST",
  //     headers: {
  //       "Content-Type": "application/json",
  //     },
  //     body: JSON.stringify({ primitive_tasks, session_id }),
  //   })
  //     .then((response) => response.json())
  //     .then((data) => {
  //       compiling = false;
  //       primitive_tasks = data.primitive_tasks;
  //       execution_states = data.execution_state;
  //       console.log({ data });
  //     })
  //     .catch((error) => {
  //       console.error("Error:", error);
  //     });
  // }

  function handleExecute(
    execute_node: tPrimitiveTaskDescription & tPrimitiveTaskExecution
  ) {
    console.log("Executing...", { execute_node, session_id });
    fetch(`${server_address}/primitive_task/execute/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ execute_node, session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        primitiveTaskExecutionStates.execution_states = data.execution_state;
        console.log("execution: ", data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function handleAddTask() {
    primitiveTaskState.add();
    update_with_server();
  }

  function handleDeleteTask(task: tPrimitiveTaskDescription) {
    console.log("delete: ", { task });
    primitiveTaskState.delete(task.id);
    const task_dict = primitive_tasks.reduce((acc, task) => {
      acc[task.id] = task;
      return acc;
    }, {});
    // update the parentIds of the children
    task.children.forEach((child_task_id) => {
      task_dict[child_task_id].parentIds = task_dict[
        child_task_id
      ].parentIds.filter((id) => id !== task.id);
    });

    // update the childrenIds of the parent
    task.parentIds.forEach((parent_task_id) => {
      task_dict[parent_task_id].children = task_dict[
        parent_task_id
      ].children.filter((id) => id !== task.id);
    });
    update_with_server();
  }

  function update_with_server() {
    fetch(`${server_address}/primitive_tasks/update/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ primitive_tasks, session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  const updateGlobalLinks: Function = getContext("updateGlobalLinks");
  onMount(() => {
    dag_renderer.init(updateGlobalLinks);
    update_dag(primitive_tasks);
  });
</script>

<div class="flex flex-col gap-y-1 grow">
  <div
    class="relative bg-[#f2f8fd] w-full flex justify-center z-10"
    class:loading-canvas={converting}
  >
    <span class="text-[1.5rem] text-slate-600 font-semibold italic">
      Execution
    </span>
    <div class="absolute right-3 top-0 bottom-0 flex items-center gap-x-2">
      <button
        class="flex items-center justify-center p-0.5 hover:bg-blue-300 rounded-full outline-2 outline-gray-800"
        onclick={handleAddTask}
      >
        <img src="plus.svg" alt="add" class="w-4 h-4" />
      </button>
    </div>
  </div>

  <!-- style:height={Math.max(
      primitive_tasks.length * 2 * node_size[1] * 1.5,
      800
    ) + "px"} -->
  <div class="relative flex flex-col gap-y-1 grow">
    {#if converting}
      <div
        class="absolute top-0 left-0 right-0 flex items-center justify-center"
      >
        <div class="flex gap-x-2">
          <img
            src="loader_circle.svg"
            class="w-6 h-6 animate-spin opacity-50"
            alt="loading"
          />
          <span class="animate-pulse">Converting...</span>
        </div>
      </div>
    {/if}
    <svg id={svgId} class="w-full h-full absolute"></svg>
    <div class="primitive-tasks relative w-full flex flex-col-reverse">
      {#each primitive_tasks as task, index}
        <div
          class="primitive-task-card-container absolute task-wrapper bg-blue-200 flex outline-1 outline-gray-300 rounded-sm shadow transition-all"
          style:z-index={primitive_tasks.length - index}
          data-id={task.id}
        >
          <PrimitiveTaskCard
            {task}
            expand={task_card_expanded.includes(task.id)}
            {compiling}
            executable={primitiveTaskExecutionStates.executable(task.id)}
            {handleExecute}
            {handleDeleteTask}
            handleInspectTask={handleInspectPrimitiveTask}
            handleToggleExpand={() => handleToggleExpand(task.id)}
          ></PrimitiveTaskCard>
        </div>
      {/each}
    </div>
    <!-- <button
      class="self-end py-1 px-2 bg-gray-100 min-w-[10rem] w-min flex justify-center rounded outline outline-gray-200 z-10 mx-2"
      class:disabled={primitive_tasks === undefined}
      tabindex="0"
      onclick={() => handleCompile()}
      onkeyup={() => {}}
    >
      Compile Graph
    </button> -->
  </div>
</div>

<style lang="postcss">
  .disabled {
    @apply opacity-50 pointer-events-none;
  }

  .loading-canvas {
    position: relative;
    background: linear-gradient(
      90deg,
      #c2e2fd 20%,
      #87f2f7 40%,
      #86c6ff 60%,
      transparent 80%
    );
    background-size: 200% 200%;
    animation: dash 3s linear infinite;
    border: 4px solid transparent;
  }
</style>
