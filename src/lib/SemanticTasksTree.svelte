<script lang="ts">
  import { server_address } from "constants";
  import * as d3 from "d3";
  import { onMount, tick } from "svelte";
  import type { tSemanticTask, tNode, tControllers } from "types";
  import { DAG } from "renderer/dag";
  import SemanticTaskCard from "./SemanticTaskCard.svelte";
  import { fly, fade, blur } from "svelte/transition";
  import { draggable } from "./draggable";
  import { getContext } from "svelte";
  let {
    semantic_tasks = $bindable([]),
    next_expansion = $bindable(undefined),
    max_value_path,
    decomposing_goal,
    handleConvert,
  }: {
    semantic_tasks: tSemanticTask[];
    next_expansion: tSemanticTask | undefined;
    max_value_path: [string[], number];
    decomposing_goal: boolean;
    handleConvert: Function;
  } = $props();
  $inspect(max_value_path);
  const session_id = (getContext("session_id") as Function)();
  const id_key = "MCT_id"; // id key for the semantic task
  // const id_key = "id"; // id key for the semantic task
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
  let controllers: tControllers = $state({
    show_max_value_path: false,
    show_next_expansion: true,
    show_new_nodes: true,
  });

  $effect(() => {
    update_dag(semantic_tasks_flattened, max_value_path, controllers);
  });
  $effect(() => {
    dag_renderer.update_next_expansion_link(next_expansion?.[id_key]);
  });
  /**
   * Stores the id of the tasks with explanation shown
   */
  let task_card_show_explanation: string[] = $state([]);

  /**
   * Stores the id of the tasks that are expanded
   */
  let task_card_expanded: string[] = $state([]);
  //   let semantic_task_nodes: tNode[] = $derived(flatten(semantic_tasks));
  const svgId = "dag-svg";
  const node_size: [number, number] = [500, 250];
  let dag_renderer = new DAG(
    svgId,
    node_size,
    ".semantic-task-card-container",
    ".semantic-tasks"
  );

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
      // if (task.label === "END") continue;
      flattened.push(task);
      if (
        task?.sub_tasks &&
        _semantic_tasks_show_sub_tasks.includes(task[id_key])
      ) {
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
  async function update_dag(
    _semantic_tasks_flattened: tSemanticTask[],
    _max_value_path: [string[], number],
    _controllers: tControllers
  ) {
    console.log("updating semantic dag:", _semantic_tasks_flattened);
    // get the bounding box of each task card
    const semantic_task_divs: NodeListOf<HTMLElement> =
      document.querySelectorAll(".semantic-task-card-container");
    const dag_data: tNode[] = Array.from(semantic_task_divs).map((div) => {
      const id = div.dataset.id || "";
      const node_data: tSemanticTask = _semantic_tasks_flattened.find(
        (task) => task[id_key] === id
      )!;
      const transform_scale =
        div.style.transform === ""
          ? 1
          : d3.zoomTransform(d3.select(`#${svgId}`).node()).k;
      return {
        id: node_data["MCT_id"],
        parentIds: node_data["MCT_parent_id"]
          ? [node_data["MCT_parent_id"]]
          : [],
        data: node_data,
        bbox: {
          ...div.getBoundingClientRect(),
          width: div.getBoundingClientRect().width / transform_scale,
          height: div.getBoundingClientRect().height / transform_scale,
        },
      };
    });

    // call renderer
    dag_renderer.update(
      dag_data,
      semantic_tasks_show_sub_tasks,
      _max_value_path[0],
      _controllers
    );
  }

  // UI handlers
  function handleToggleShowSubTasks(task_id: string) {
    semantic_tasks_show_sub_tasks = semantic_tasks_show_sub_tasks.includes(
      task_id
    )
      ? semantic_tasks_show_sub_tasks.filter((id) => id !== task_id)
      : [...semantic_tasks_show_sub_tasks, task_id];
  }

  async function handleToggleExpand(task_id: string) {
    task_card_expanded = task_card_expanded.includes(task_id)
      ? task_card_expanded.filter((id) => id !== task_id)
      : [...task_card_expanded, task_id];

    // trigger re-render
    await tick();
    update_dag(semantic_tasks_flattened, max_value_path, controllers);
  }

  function handleToggleExplain(task_id: string) {
    task_card_show_explanation = task_card_show_explanation.includes(task_id)
      ? task_card_show_explanation.filter((id) => id !== task_id)
      : [...task_card_show_explanation, task_id];
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

  function handleSetAsNextExpansion(task: tSemanticTask) {
    next_expansion = task;
    // dag_renderer.update_next_expansion_link(next_expansion[id_key]);
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

  function navigateToNextExpansion() {}

  onMount(() => {
    dag_renderer.init();
    update_dag(semantic_tasks, max_value_path, controllers);
  });
</script>

<div class="flex flex-col grow">
  <div class="relative bg-orange-100 w-full flex justify-center z-10">
    <span
      class="canvas-header text-[1.5rem] text-slate-600 font-semibold italic"
    >
      Semantic Tasks
    </span>
    <div class="absolute right-3 top-0 bottom-0 flex items-center gap-x-2">
      <button
        class="flex items-center justify-center p-0.5 hover:bg-orange-300 rounded-full outline-2 outline-gray-800"
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
  <div class="relative bg-gray-50 flex flex-col gap-y-1 grow">
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
    <svg id={svgId} class="dag-svg w-full h-full absolute"></svg>
    <div class="semantic-tasks relative w-full">
      <button
        class="next-expansion-legend text-orange-900 font-mono absolute left-1/2 top-1 -translate-x-1/2 px-2 py-1 rounded outline-3 outline-orange-500 outline-dashed bg-[#fbfaec]"
        class:inactive={!controllers.show_next_expansion}
        onclick={() => {
          controllers.show_next_expansion = !controllers.show_next_expansion;
          d3.select(`#${svgId}`)
            .select(".next_expansion_link")
            .attr("opacity", controllers.show_next_expansion ? 1 : 0);
        }}
      >
        Next Expansion
      </button>
      <button
        class="new-node-legend text-orange-900 font-mono absolute text-xs left-[calc(50%+8rem)] top-2 -translate-x-1/2 px-2 py-1 rounded bg-orange-200"
        class:inactive={!controllers.show_new_nodes}
        onclick={() => {
          controllers.show_new_nodes = !controllers.show_new_nodes;
        }}
      >
        New Nodes
      </button>
      <button
        class="best-path-legend text-orange-900 font-mono font-bold absolute text-xs left-[calc(50%-8.1rem)] top-1.5 -translate-x-1/2 px-2 py-1 rounded bg-[#fbfaec] border-3 border-black"
        class:inactive={!controllers.show_max_value_path}
        onclick={() =>
          (controllers.show_max_value_path = !controllers.show_max_value_path)}
      >
        Best Path
      </button>

      {#each semantic_tasks_flattened as task, index}
        <!-- use:draggable={dag_renderer} -->
        <div
          class="semantic-task-card-container w-max absolute flex task-wrapper transition-all duration-500"
          style:z-index={semantic_tasks_flattened.length - index}
          data-id={task[id_key]}
        >
          <SemanticTaskCard
            {task}
            {id_key}
            {controllers}
            next_expansion={(next_expansion &&
              next_expansion[id_key] === task[id_key]) ||
              false}
            on_max_value_path={max_value_path[0].includes(task[id_key])}
            expand={task_card_expanded.includes(task[id_key])}
            show_explanation={task_card_show_explanation.includes(task[id_key])}
            handleSetAsNextExpansion={() => handleSetAsNextExpansion(task)}
            {handleDecompose}
            {handleDeleteSubTasks}
            {handleToggleShowSubTasks}
            {handleDeleteTask}
            handleToggleExpand={() => handleToggleExpand(task[id_key])}
            handleToggleExplain={() => handleToggleExplain(task[id_key])}
          ></SemanticTaskCard>
          <!-- {#if task_card_expanded.includes(task[id_key]) && !task_card_show_explanation.includes(task[id_key])}
            <button
              class="flex p-0.5 hover:bg-orange-400 justify-center"
              onclick={() =>
                (task_card_show_explanation = [
                  ...task_card_show_explanation,
                  task[id_key],
                ])}
            >
              <img
                src="chevron_right.svg"
                class="mt-0.5 w-5 h-4 pointer-events-none"
                alt="handle"
              />
            </button>
          {/if} -->
        </div>
      {/each}
    </div>
    {#if semantic_tasks_flattened.length > 0}
      <button
        class="self-end py-1 mx-2 bg-gray-100 min-w-[10rem] w-min flex justify-center rounded outline outline-gray-200 z-10"
        tabindex="0"
        onclick={() => handleConvert()}
        onkeyup={() => {}}
      >
        Convert
      </button>
    {/if}
  </div>
</div>

<style lang="postcss">
  @reference "../app.css";
  .inactive {
    @apply opacity-50;
  }
  .inactive:hover {
    @apply opacity-100 scale-110 transition-all;
  }
</style>
