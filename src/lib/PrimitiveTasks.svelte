<script lang="ts">
  import { server_address } from "constants";
  import { onMount, tick } from "svelte";
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
    tExecutionState,
    tNode,
    tTask,
  } from "types";
  import { DAG } from "renderer/dag";
  import PrimitiveTaskCard from "./PrimitiveTaskCard.svelte";
  import { fly, fade, blur } from "svelte/transition";
  import { draggable } from "./draggable";
  import { getContext } from "svelte";
  let {
    primitive_tasks,
    converting,
    handleInspectPrimitiveTask = () => {},
  }: {
    primitive_tasks: (tPrimitiveTaskDescription &
      Partial<tPrimitiveTaskExecution>)[];
    converting: boolean;
    handleInspectPrimitiveTask: Function;
  } = $props();
  let task_card_expanded: string[] = $state([]);
  let execution_states: Record<string, tExecutionState> | undefined =
    $state(undefined);
  let compiling = $state(false);
  const session_id = (getContext("session_id") as Function)();
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "dag-svg";
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

  /**
   * Prepare the data for the dag renderer
   * by adding the bounding box of each task card
   * @param _primitive_tasks
   */
  function update_dag(_primitive_tasks: tPrimitiveTaskDescription[]) {
    console.log("updating primitive dag:", _primitive_tasks);
    // get the bounding box of each task card
    const primitive_task_divs = document.querySelectorAll(
      ".primitive-task-card-container"
    );
    const dag_data: tNode[] = Array.from(primitive_task_divs).map((div) => {
      const id = (div as HTMLElement).dataset.id;
      const node_data: tPrimitiveTaskDescription = _primitive_tasks.find(
        (task) => task.id === id
      )!;
      return {
        ...node_data,
        bbox: div.getBoundingClientRect(),
      };
    });

    // call renderer
    dag_renderer.update(dag_data, []);
  }

  // UI handlers
  function handleToggleExpand(task_id: string) {
    task_card_expanded = task_card_expanded.includes(task_id)
      ? task_card_expanded.filter((id) => id !== task_id)
      : [...task_card_expanded, task_id];
  }

  // handlers with server-side updates
  function handleCompile() {
    console.log("Compiling...", { primitive_tasks, session_id });
    compiling = true;
    fetch(`${server_address}/primitive_task/compile/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ primitive_tasks, session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        compiling = false;
        primitive_tasks = data.primitive_tasks;
        execution_states = data.execution_state;
        console.log({ data });
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

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
        execution_states = data.execution_state;
        console.log("execution: ", data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function handleAddTask() {
    primitive_tasks = [
      ...primitive_tasks,
      {
        id: Math.random().toString(),
        label: "New Task",
        description: "New Task Description",
        explanation: "N/A",
        parentIds: [],
        children: [],
        confidence: 0.5,
        complexity: 0.5,
      },
    ];
    update_with_server();
  }

  function handleDeleteTask(task: tPrimitiveTaskDescription) {
    console.log("delete: ", { task });
    primitive_tasks = primitive_tasks.filter((_task) => _task.id !== task.id);
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

  onMount(() => {
    dag_renderer.init();
    update_dag(primitive_tasks);
    console.log({ execution_states });
  });
</script>

<div class="flex flex-col gap-y-1 grow h-fit">
  <div class="relative bg-[#f2f8fd] w-full flex justify-center z-10">
    <span class="text-[1.5rem] text-slate-600 font-semibold italic">
      Primitive Tasks
    </span>
    <div class="absolute left-3 top-0 bottom-0 flex items-center gap-x-2">
      <button
        class="flex items-center justify-center p-0.5 hover:bg-orange-500 rounded-full outline outline-2 outline-gray-800"
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
  <div class="relative bg-gray-50 flex flex-col gap-y-1 h-[1000px]">
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
    <div
      class="py-1 px-2 bg-gray-100 min-w-[10rem] w-min flex justify-center mt-2 rounded outline outline-gray-200 z-10 mx-2"
      class:disabled={primitive_tasks === undefined}
      tabindex="0"
      role="button"
      onclick={() => handleCompile()}
      onkeyup={() => {}}
    >
      Compile Graph
    </div>
    <svg id={svgId} class="w-full h-full absolute"></svg>
    <div class="primitive-tasks relative w-full flex flex-col-reverse">
      {#each primitive_tasks as task, index}
        <div
          class="primitive-task-card-container absolute task-wrapper bg-blue-200 flex outline outline-1 outline-gray-300 rounded-sm shadow"
          style:z-index={primitive_tasks.length - index}
          data-id={task.id}
        >
          <PrimitiveTaskCard
            {task}
            expand={task_card_expanded.includes(task.id)}
            {compiling}
            executable={execution_states?.[task.id].executable || false}
            {handleExecute}
            {handleDeleteTask}
            handleInspectTask={handleInspectPrimitiveTask}
            handleToggleExpand={() => handleToggleExpand(task.id)}
          ></PrimitiveTaskCard>
          {#if !task_card_expanded.includes(task.id)}
            <button
              class="flex p-0.5 hover:bg-blue-400 justify-center"
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
  </div>
</div>

<style lang="postcss">
  .disabled {
    @apply opacity-50 pointer-events-none;
  }
</style>
