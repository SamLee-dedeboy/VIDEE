<script lang="ts">
  import { server_address } from "constants";
  import { onMount, setContext, tick } from "svelte";
  import type { tPrimitiveTaskDescription, tNode, tPrimitiveTask } from "types";
  import * as d3 from "d3";
  import { DAG } from "renderer/dag";
  import PrimitiveTaskCard from "./PrimitiveTaskCard.svelte";
  import { getContext } from "svelte";
  import {
    session_id,
    primitiveTaskState,
    primitiveTaskExecutionStates,
  } from "../ExecutionStates.svelte";
  let {
    converting,
    compiling,
    handleInspectPrimitiveTask = () => {},
  }: {
    converting: boolean;
    compiling: boolean | string | undefined;
    handleInspectPrimitiveTask: Function;
  } = $props();

  let primitiveTaskOptions: {
    label: string;
    definition: string;
  }[] = $state([]);
  let executing_task_id: string | undefined = $state(undefined);
  let ask_to_check_results = $state(false);
  let executed_task_id: string | undefined = $state(undefined);
  const primitive_tasks = $derived(
    primitiveTaskState.primitiveTasks
  ) as tPrimitiveTaskDescription[];
  let task_card_expanded: string[] = $state([]);
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
      const parentIds =
        node_data.id === "-1"
          ? []
          : node_data.parentIds.length === 0
            ? ["-1"]
            : node_data.parentIds;
      return {
        ...node_data,
        parentIds: parentIds,
        data: node_data,
        bbox: {
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
  const handleCompile: Function = getContext("handleCompile");
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

  function handleExecute(execute_node: tPrimitiveTask) {
    console.log("Executing...", { execute_node, session_id });
    executing_task_id = execute_node.id;

    fetch(`${server_address}/primitive_task/execute/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        execute_node: execute_node,
        parent_node_id:
          execute_node.parentIds.length === 0
            ? null
            : execute_node.parentIds[0],
        session_id,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        primitiveTaskState.reset_flags();
        primitiveTaskExecutionStates.execution_states = data.execution_state;
        console.log("execution: ", data);
        executed_task_id = executing_task_id;
        executing_task_id = undefined;
        ask_to_check_results = true;
      })
      .catch((error) => {
        console.error("Error:", error);
        executing_task_id = undefined;
      });
  }

  function navigate_to_results(node_id: string) {
    console.log("navigating to results: ", node_id);
    const task = primitive_tasks.find((task) => task.id === node_id);
    handleInspectPrimitiveTask(task, true);
  }

  function handleAddTask() {
    primitiveTaskState.addTask();
    // update_with_server();
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
    // update_with_server();
  }

  // function update_with_server() {
  //   fetch(`${server_address}/primitive_tasks/update/`, {
  //     method: "POST",
  //     headers: {
  //       "Content-Type": "application/json",
  //     },
  //     body: JSON.stringify({ primitive_tasks, session_id }),
  //   })
  //     .then((response) => response.json())
  //     .then((data) => {
  //       console.log(data);
  //     })
  //     .catch((error) => {
  //       console.error("Error:", error);
  //     });
  // }

  function fetchPrimitiveTaskOptions() {
    fetch(`${server_address}/primitive_task/list/`)
      .then((response) => response.json())
      .then((data) => {
        primitiveTaskOptions = data;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
  const updateGlobalLinks: Function = getContext("updateGlobalLinks");
  onMount(() => {
    fetchPrimitiveTaskOptions();
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
        title="Add Node"
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
    <svg id={svgId} class="w-full h-full absolute overflow-visible"></svg>
    <div class="primitive-tasks relative w-full flex flex-col-reverse">
      {#each primitive_tasks as task, index}
        <div
          class="primitive-task-card-container absolute task-wrapper bg-blue-200 flex outline-1 outline-gray-300 rounded-sm shadow transition-all"
          class:executing={executing_task_id === task.id}
          data-id={task.id}
          style={`z-index: ${primitive_tasks.length - index}`}
        >
          {#if ask_to_check_results && executed_task_id === task.id}
            <div
              class="absolute bottom-[calc(100%+2px)] left-1/2 -translate-x-1/2 flex justify-center z-20"
            >
              <div
                class="rounded w-max bg-[#f6faff] outline-0 outline-gray-200 border-t-6 border-blue-200 shadow-[0px_0px_1px_1px_lightgray] px-2 py-1 flex items-center font-mono gap-x-8"
              >
                <span class="text-slate-600 font-semibold italic">
                  Execution Complete!
                </span>
                <div
                  class="flex justify-between text-sm gap-x-2 self-end italic"
                >
                  <button
                    class="bg-green-100 outline-2 outline-gray-200 hover:bg-green-200 px-2 py-1 rounded text-slate-600"
                    onclick={() => {
                      ask_to_check_results = false;
                      navigate_to_results(executed_task_id!);
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

          <PrimitiveTaskCard
            label_options={primitiveTaskOptions}
            add_parent_options={primitive_tasks
              .filter(
                (t) =>
                  t.id !== task.id &&
                  !task.parentIds.includes(t.id) &&
                  !task.children.includes(t.id)
              )
              .map((t) => [t.id, t.label])}
            remove_parent_options={task.parentIds.map((id) => [
              id,
              primitive_tasks.find((t) => t.id === id)!.label,
            ])}
            {task}
            expand={task_card_expanded.includes(task.id)}
            {compiling}
            executable={primitiveTaskExecutionStates.executable(task.id)}
            {handleExecute}
            {handleCompile}
            {handleDeleteTask}
            handleInspectTask={handleInspectPrimitiveTask}
            handleToggleExpand={() => handleToggleExpand(task.id)}
            handleAddParent={(parent_id) =>
              primitiveTaskState.addParent(task, parent_id)}
            handleRemoveParent={(parent_id) =>
              primitiveTaskState.removeParent(task, parent_id)}
          ></PrimitiveTaskCard>
        </div>
      {/each}
    </div>
    {#if primitive_tasks.length > 0}
      <button
        class=" self-end font-mono text-sm bg-blue-50 text-slate-700 hover:bg-blue-100 px-2 py-1 mx-2 w-min flex gap-x-2 items-center justify-center rounded outline-2 outline-blue-200 z-10"
        class:disabled={primitive_tasks === undefined}
        tabindex="0"
        onclick={() => handleCompile()}
        onkeyup={() => {}}
      >
        <svg
          class="w-5 h-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#405065"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          ><circle cx="12" cy="12" r="10" /><path d="m14.31 8 5.74 9.94" /><path
            d="M9.69 8h11.48"
          /><path d="m7.38 12 5.74-9.94" /><path d="M9.69 16 3.95 6.06" /><path
            d="M14.31 16H2.83"
          /><path d="m16.62 12-5.74 9.94" /></svg
        >
        Compile
      </button>
    {/if}
    <button
      class="absolute left-2 top-2 bg-blue-50 font-mono hover:bg-blue-100 p-1 flex justify-center items-center rounded outline-2 outline-blue-200 z-10"
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
  @reference "tailwindcss";
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
