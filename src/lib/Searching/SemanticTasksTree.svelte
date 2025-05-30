<script lang="ts">
  import { evaluation_colors, server_address } from "constants";
  import * as d3 from "d3";
  import { onMount, tick, getContext } from "svelte";
  import type { tSemanticTask, tNode, tControllers } from "types";
  import { DAG } from "renderer/dag";
  import SemanticTaskCard from "./SemanticTaskCard.svelte";
  import { fade } from "svelte/transition";
  import AddMctNode from "./AddMCTNode.svelte";
  import {
    likert_scale_num,
    semanticTaskPlanState,
  } from "lib/ExecutionStates.svelte";
  import ColorScaleLegend from "./ColorScaleLegend.svelte";
  let {
    semantic_tasks = $bindable([]),
    next_expansion = $bindable(undefined),
    streaming_states = $bindable({
      started: false,
      paused: false,
      finished: false,
    }),
    selected_semantic_task_path = $bindable([]),
    decomposing_goal,
    handleRegenerate = () => {},
  }: {
    semantic_tasks: tSemanticTask[];
    next_expansion: tSemanticTask | undefined;
    streaming_states: {
      started: boolean;
      paused: boolean;
      finished: boolean;
    };
    selected_semantic_task_path: tSemanticTask[];
    decomposing_goal: boolean;
    handleRegenerate: Function;
  } = $props();
  const id_key = "MCT_id"; // id key for the semantic task
  let select_strategy = $derived(semanticTaskPlanState.select_strategy);
  // const id_key = "id"; // id key for the semantic task
  /**
   * Stores the id of the expanded tasks
   */
  let semantic_tasks_hide_children: string[] = $state([]);
  /**
   * Stores the flattened semantic tasks
   */
  let semantic_tasks_flattened: tSemanticTask[] = $derived(
    hide_children(semantic_tasks, semantic_tasks_hide_children)
  );
  let max_value_path: string[] = $derived(
    selected_semantic_task_path.map((t) => t[id_key])
  );
  let controllers: tControllers = $state({
    show_max_value_path: true,
    show_next_expansion: true,
    show_new_nodes: true,
    show_complexity: true,
    show_coherence: true,
    show_importance: true,
  });
  let streaming = $derived(
    streaming_states.started &&
      !streaming_states.paused &&
      !streaming_states.finished
  );
  let adding_child = $state(false);
  let adding_child_for: tSemanticTask | undefined = $state(undefined);

  $effect(() => {
    update_dag(semantic_tasks_flattened, max_value_path, controllers);
  });
  $effect(() => {
    dag_renderer.update_next_expansion_link(next_expansion?.[id_key]);
  });

  const updateNodeValue: Function = getContext("updateNodeValue");
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

  function hide_children(
    _semantic_tasks: tSemanticTask[] | undefined,
    _semantic_tasks_hide_children: string[]
  ) {
    console.log({ _semantic_tasks, _semantic_tasks_hide_children });
    // flatten the semantic tasks with bfs
    if (!_semantic_tasks) return [];
    // const queue = [..._semantic_tasks];
    const queue = _semantic_tasks.filter(
      (t) => t.label !== "END" && t.parentIds.length === 0
    );
    const flattened: tSemanticTask[] = [];
    while (queue.length) {
      let task = queue.shift()!;
      flattened.push(task);
      if (task[id_key] === "-1") continue;
      if (_semantic_tasks_hide_children.includes(task[id_key])) continue;
      if (task?.MCT_children_ids) {
        const children_nodes = task.MCT_children_ids.map((child_id) =>
          _semantic_tasks.find((t) => t[id_key] === child_id)
        ).filter((t) => t !== undefined) as tSemanticTask[];
        queue.push(...children_nodes);
      }
      // if (
      //   task?.sub_tasks &&
      //   _semantic_tasks_show_sub_tasks.includes(task[id_key])
      // ) {
      //   queue.push(...task.sub_tasks);
      // }
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
    _best_path: string[],
    _controllers: tControllers
  ) {
    console.log(
      "updating semantic dag:",
      $state.snapshot(_semantic_tasks_flattened)
    );
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
        id: node_data[id_key],
        parentIds: node_data.MCT_parent_id ? [node_data.MCT_parent_id] : [],
        data: node_data,
        bbox: {
          ...div.getBoundingClientRect(),
          width: div.getBoundingClientRect().width / transform_scale,
          height: div.getBoundingClientRect().height / transform_scale,
        },
      };
    });

    // call renderer
    dag_renderer.update(dag_data, _best_path, _controllers, true);
  }

  // UI handlers
  function handleToggleShowSubTasks(task_id: string) {
    // semantic_tasks_show_sub_tasks = semantic_tasks_show_sub_tasks.includes(
    //   task_id
    // )
    //   ? semantic_tasks_show_sub_tasks.filter((id) => id !== task_id)
    //   : [...semantic_tasks_show_sub_tasks, task_id];
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

  function addChild(name: string, description: string, task: tSemanticTask) {
    const new_task: tSemanticTask = {
      id: "" + (+task.level + 1),
      parentIds: [task.id],
      children: [],
      sub_tasks: [],
      new_node: false,
      level: +task.level + 1,
      llm_evaluation: {
        complexity: likert_scale_num,
        coherence: likert_scale_num,
        importance: likert_scale_num,
        complexity_reason: "",
        coherence_reason: "",
        importance_reason: "",
      },
      user_evaluation: {
        complexity: likert_scale_num,
        coherence: likert_scale_num,
        importance: likert_scale_num,
        complexity_reason: "",
        coherence_reason: "",
        importance_reason: "",
      },
      value: 1.0,
      visits: 0,
      path_value: task.path_value,
      MCT_id: task.MCT_children_ids.length.toString(),
      label: name,
      description: description,
      explanation: "N/A",
      MCT_parent_id: task[id_key],
      MCT_children_ids: [],
    };
    adding_child = false;
    adding_child_for = undefined;
    semantic_tasks.push(new_task);
    task.MCT_children_ids.push(new_task[id_key]);
    // update_with_server();
  }

  function handleDeleteTask(task: tSemanticTask) {
    const task_dict = semantic_tasks.reduce((acc, task) => {
      acc[task[id_key]] = task;
      return acc;
    }, {});

    //
    // update the dependencies
    //
    // update the parentIds of the children
    // task.children?.forEach((child_task_id) => {
    //   task_dict[child_task_id].parentIds = task_dict[
    //     child_task_id
    //   ].parentIds.filter((id) => id !== task.id);
    // });

    // update the childrenIds of the parent
    // task.parentIds.forEach((parent_task_id) => {
    //   task_dict[parent_task_id].children = task_dict[
    //     parent_task_id
    //   ].children.filter((id) => id !== task.id);
    // });
    // if (task[id_key] === next_expansion?.[id_key]) {
    //   next_expansion = undefined;
    // }

    // delete this node from its parent's children_ids
    const parent = task_dict[task.MCT_parent_id];
    parent.MCT_children_ids = parent.MCT_children_ids.filter(
      (id) => id !== task[id_key]
    );
    task_dict[task.MCT_parent_id] = parent;

    // delete the branch in the Monte Carlo Tree
    let queue = [task];
    while (queue.length) {
      const task = queue.shift()!;
      const children = task.MCT_children_ids.map((id) => task_dict[id]);
      queue.push(...children);
      semantic_tasks = semantic_tasks.filter(
        (_task) => _task[id_key] !== task[id_key]
      );
    }
    updateNodeValue();
    // update_with_server();
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
  }

  function handleTaskHovered(task_id: string, hovered: boolean) {
    const hovered_path_ids = hovered ? trace_path(semantic_tasks, task_id) : [];
    update_hovered_path(hovered_path_ids, hovered);
    dag_renderer.update_links(
      controllers.show_max_value_path
        ? hovered_path_ids.concat(max_value_path)
        : hovered_path_ids,
      true
    );
  }

  function update_hovered_path(path_ids: string[], hovered: boolean) {
    document
      .querySelectorAll(".semantic-task-card-container")
      .forEach((div) => {
        const id = (div as HTMLElement).dataset.id || "";
        if (hovered) {
          div.classList.add("not-on-hovered-path");
          if (path_ids.includes(id)) {
            div.classList.remove("not-on-hovered-path");
            div.classList.add("on-hovered-path");
          }
        } else {
          div.classList.remove("not-on-hovered-path");
          div.classList.remove("on-hovered-path");
        }
      });
  }

  function handleSelectPath(task: tSemanticTask) {
    console.log("handle select path", task);
    const path_ids = trace_path(semantic_tasks, task[id_key]);
    selected_semantic_task_path = path_ids.map(
      (id) => semantic_tasks.find((task) => task[id_key] === id)!
    );
  }

  function handleClear() {
    selected_semantic_task_path = [];
    semantic_tasks = [];
    next_expansion = undefined;
    streaming_states = {
      started: false,
      paused: false,
      finished: false,
    };
  }

  function trace_path(
    _semantic_tasks: tSemanticTask[],
    task_id: string
  ): string[] {
    const path: string[] = [];
    const task_dict = _semantic_tasks.reduce((acc, task) => {
      acc[task[id_key]] = task;
      return acc;
    }, {});
    let task = task_dict[task_id];
    while (task) {
      path.push(task[id_key]);
      const parent_id = task["MCT_parent_id"];
      task = parent_id ? task_dict[parent_id] : null;
    }
    return path;
  }

  onMount(() => {
    dag_renderer.init();
    update_dag(semantic_tasks, max_value_path, controllers);
  });
</script>

{#snippet complexity_icon()}
  <img src="network.svg" alt="complexity" class="pointer-events-none" />
{/snippet}

{#snippet coherence_icon()}
  <img src="waveform.svg" alt="coherence" class="pointer-events-none" />
{/snippet}

{#snippet importance_icon()}
  <img src="cpu.svg" alt="importance" class="pointer-events-none" />
{/snippet}

<div class="flex flex-col gap-y-1 grow">
  <div class="relative bg-orange-100 w-full flex justify-center z-10">
    <span class="flex">
      <span
        class="canvas-header text-[1.5rem] text-slate-600 font-semibold italic relative"
      >
        Searching Tree
        <span
          class="info-trigger cursor-help absolute w-max text-sm left-[calc(100%+1rem)] bottom-0 flex flex-col gap-y-2"
        >
          <div class="flex items-center gap-x-1 underline relative">
            <img src="info.svg" class="w-5 h-5" alt="info" />Tip: Exploitation
            vs. Exploration
          </div>
          <div
            class="info scale-0 absolute top-[calc(100%+0.15rem)] left-1/2 -translate-x-1/3 flex flex-wrap w-[25rem] text-sm text-slate-500 mt-[-0.15rem] pt-[0.15rem]"
          >
            <span class="outline-2 outline-slate-700 p-2 rounded bg-gray-50">
              A good searching process would balance between
              <span class="font-bold text-black"
                >sticking to what seems best (exploitation)
              </span>
              and <br />
              <span class="font-bold text-black"
                >trying new options (exploration)
              </span>
              to make the best decision. If only exploits, you might miss better
              choices; If only explores, you waste time on uncertain options.
            </span>
          </div>
        </span>
      </span>
    </span>
  </div>

  <div class="relative bg-gray-50 flex flex-col gap-y-1 grow">
    {#if adding_child && adding_child_for}
      <div
        in:fade={{ duration: 100 }}
        class="absolute left-0 right-0 bottom-0 top-0 z-30"
      >
        <div
          class="absolute left-0 right-0 bottom-0 top-0 bg-gray-200 opacity-50"
        ></div>
        <div
          class="absolute left-1/2 top-1/4 -translate-x-1/2 -translate-y-1/4 p-2 flex flex-col min-w-[15rem] min-h-[15rem] bg-orange-50 outline-2 outline-orange-100"
        >
          <AddMctNode
            {adding_child_for}
            handleAddChild={addChild}
            handleCancel={() => {
              adding_child = false;
              adding_child_for = undefined;
            }}
          />
        </div>
      </div>
    {/if}
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
      <!-- <div
        class="absolute bg-[#fafafa] left-[calc(50%-5.3rem)] w-[20.7rem] h-[3rem] rounded shadow-md"
      ></div> -->
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
      <div
        class="select-strategy-legend font-mono absolute text-xs left-[calc(50%+10.5rem)] top-0 -translate-x-1/2 flex flex-col gap-y-1 items-center"
      >
        Selection Strategy:
        <div
          class=" text-orange-900 font-mono rounded outline-2 outline-orange-500 bg-[#fbfaec] divide-x-2 divide-orange-500 flex"
        >
          <button
            class="px-2 py-1 hover:!opacity-100 hover:scale-110 transition-all"
            class:inactive={select_strategy !== "UCT"}
            onclick={() => (semanticTaskPlanState.select_strategy = "UCT")}
            >Balanced</button
          >
          <button
            class="px-2 py-1 hover:!opacity-100 hover:scale-110 transition-all"
            class:inactive={select_strategy !== "greedy"}
            onclick={() => (semanticTaskPlanState.select_strategy = "greedy")}
            >Exploit</button
          >
        </div>
      </div>
      <button
        class="new-node-legend font-bold text-orange-900 font-mono absolute text-xs left-[calc(50%+25rem)] top-2 -translate-x-1/2 px-2 py-1 rounded outline-2 outline-orange-900 bg-[#fbfaec]"
        class:inactive={!controllers.show_new_nodes}
        onclick={() => {
          controllers.show_new_nodes = !controllers.show_new_nodes;
        }}
      >
        New Nodes
      </button>
      <button
        class="best-path-legend text-orange-900 font-mono font-bold absolute text-xs left-[calc(50%+31rem)] top-1.5 -translate-x-1/2 px-2 py-1 rounded bg-[#fbfaec] border-2 border-black"
        class:inactive={!controllers.show_max_value_path}
        onclick={() =>
          (controllers.show_max_value_path = !controllers.show_max_value_path)}
      >
        Best Path
      </button>
      <button
        class="clear-button font-bold text-slate-500 font-mono absolute text-xs right-0 top-2 -translate-x-1/2 px-2 py-1 rounded outline-2 outline-gray-300 bg-gray-50 hover:bg-gray-200"
        class:inactive={!controllers.show_new_nodes}
        onclick={handleClear}
      >
        Clear
      </button>
      <div class="evaluation-legends-container absolute left-0 top-0">
        <ColorScaleLegend
          {controllers}
          {complexity_icon}
          {coherence_icon}
          {importance_icon}
        />
      </div>

      {#each semantic_tasks_flattened as task, index}
        <div
          class="semantic-task-card-container w-max absolute flex task-wrapper transition-all duration-500"
          style:z-index={semantic_tasks_flattened.length - index}
          data-id={task[id_key]}
        >
          <SemanticTaskCard
            {task}
            {id_key}
            {controllers}
            {streaming}
            next_expansion={(next_expansion &&
              next_expansion[id_key] === task[id_key]) ||
              false}
            on_max_value_path={max_value_path[0].includes(task[id_key])}
            expand={task_card_expanded.includes(task[id_key])}
            show_explanation={task_card_show_explanation.includes(task[id_key])}
            handleSetAsNextExpansion={() => handleSetAsNextExpansion(task)}
            {handleTaskHovered}
            {handleRegenerate}
            {handleDecompose}
            {handleToggleShowSubTasks}
            handleAddChild={() => {
              adding_child = true;
              adding_child_for = task;
            }}
            handleToggleChildren={() => {
              if (semantic_tasks_hide_children.includes(task[id_key])) {
                semantic_tasks_hide_children =
                  semantic_tasks_hide_children.filter(
                    (id) => id !== task[id_key]
                  );
              } else {
                semantic_tasks_hide_children = [
                  ...semantic_tasks_hide_children,
                  task[id_key],
                ];
              }
            }}
            {handleDeleteTask}
            {handleSelectPath}
            handleToggleExpand={() => handleToggleExpand(task[id_key])}
            handleToggleExplain={() => handleToggleExplain(task[id_key])}
            {complexity_icon}
            {coherence_icon}
            {importance_icon}
          ></SemanticTaskCard>
        </div>
      {/each}
    </div>
  </div>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .info-trigger:hover > .info {
    @apply scale-100;
    transition: all 0.3s;
  }
  .disabled {
    @apply pointer-events-none opacity-50;
  }
  .best-path-legend:hover,
  .new-node-legend:hover,
  .next-expansion-legend:hover {
    @apply scale-110 transition-all;
  }
  .inactive {
    @apply opacity-40;
  }
  .new-node-legend::before {
    content: "";
    position: absolute;
    right: calc(100% + 4px);
    top: 4px;
    width: 5px;
    height: 5px;
    background-color: #7e2a0c;
    border-radius: 50%;
    transform: translateY(-50%);
  }
</style>
