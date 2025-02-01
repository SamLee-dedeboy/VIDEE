<script lang="ts">
  import { server_address } from "constants";
  import { onMount, tick } from "svelte";
  import type { tSemanticTask, tNode } from "types";
  import { DAG } from "renderer/dag";
  import SemanticTaskCard from "./SemanticTaskCard.svelte";
  import { fly, fade, blur } from "svelte/transition";
  import { draggable } from "./draggable";
  import { getContext } from "svelte";
  let {
    semantic_tasks = $bindable([]),
    decomposing_goal,
    handleConvert,
  }: {
    semantic_tasks: tSemanticTask[];
    decomposing_goal: boolean;
    handleConvert: Function;
  } = $props();
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
    _semantic_tasks_show_sub_tasks: string[]
  ) {
    console.log({ _semantic_tasks, _semantic_tasks_show_sub_tasks });
    // flatten the semantic tasks with bfs
    if (!_semantic_tasks) return [];
    const queue = [..._semantic_tasks];
    const flattened: tSemanticTask[] = [];
    while (queue.length) {
      let task = queue.shift()!;
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
    dag_renderer.update(dag_data, semantic_tasks_show_sub_tasks);
  }

  // UI handlers
  function handleToggleShowSubTasks(task_id: string) {
    semantic_tasks_show_sub_tasks = semantic_tasks_show_sub_tasks.includes(
      task_id
    )
      ? semantic_tasks_show_sub_tasks.filter((id) => id !== task_id)
      : [...semantic_tasks_show_sub_tasks, task_id];
  }

  function handleToggleExpand(task_id: string) {
    task_card_expanded = task_card_expanded.includes(task_id)
      ? task_card_expanded.filter((id) => id !== task_id)
      : [...task_card_expanded, task_id];
  }

  // handlers with server-side updates
  function handleAddTask() {
    semantic_tasks.push({
      id: Math.random().toString(),
      label: "New Task",
      description: "New Task Description",
      explanation: "N/A",
      parentIds: [],
      sub_tasks: [],
      children: [],
      confidence: 0.0,
      complexity: 0.0,
    });
    update_with_server();
  }

  function handleDeleteTask(task: tSemanticTask) {
    semantic_tasks = semantic_tasks.filter((_task) => _task.id !== task.id);
    const task_dict = semantic_tasks.reduce((acc, task) => {
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

  function handleDeleteSubTasks(task: tSemanticTask) {
    console.log({ task, semantic_tasks });
    task.sub_tasks = [];
    semantic_tasks = semantic_tasks.map((_task) =>
      _task.id === task.id ? task : _task
    );
    update_with_server();
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

  function update_with_server() {
    fetch(`${server_address}/semantic_task/update/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ semantic_tasks, session_id }),
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
    update_dag(semantic_tasks);
  });
</script>

<div class="flex flex-col gap-y-1 grow h-fit">
  <div class="relative bg-[#FFCFB1] w-full flex justify-center z-10">
    <span class="text-[1.5rem] text-slate-600 font-semibold italic">
      Semantic Tasks
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
      semantic_tasks_flattened.length * 2 * node_size[1] * 1.5,
      1000
    ) + "px"} -->
  <div class="relative bg-gray-50 flex flex-col gap-y-1 h-[1000px]">
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
            {handleDeleteSubTasks}
            {handleToggleShowSubTasks}
            {handleDeleteTask}
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
