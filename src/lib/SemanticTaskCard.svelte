<script lang="ts">
  import type { tSemanticTask } from "types";
  import { slide, scale } from "svelte/transition";
  let {
    task,
    id_key,
    next_expansion,
    on_max_value_path = false,
    controllers,
    show_explanation = $bindable(false),
    expand,
    handleSetAsNextExpansion = () => {},
    handleDecompose = () => {},
    handleToggleExplain = () => {},
    handleToggleExpand = () => {},
    handleToggleShowSubTasks = () => {},
    handleDeleteSubTasks = () => {},
    handleDeleteTask = () => {},
  }: {
    task: tSemanticTask;
    id_key: string;
    next_expansion: boolean;
    on_max_value_path: boolean;
    controllers: {
      show_max_value_path: boolean;
      show_next_expansion: boolean;
      show_new_nodes: boolean;
    };
    show_explanation: boolean;
    expand: boolean;
    handleSetAsNextExpansion?: Function;
    handleDecompose?: Function;
    handleToggleExplain?: Function;
    handleToggleExpand?: Function;
    handleToggleShowSubTasks?: Function;
    handleDeleteSubTasks?: Function;
    handleDeleteTask?: Function;
  } = $props();
  let show_subtasks = $state(false);
  let show_actions = $state(false);
  function showSubTasks() {
    show_subtasks = !show_subtasks;
    handleToggleShowSubTasks(task[id_key]);
  }
  let isEnd = $derived(task.label === "END");
  $inspect(on_max_value_path);
</script>

<div class="container flex flex-col w-min rounded-sm">
  <div
    class="task-card text-slate-600 w-min min-w-[18rem] transition-all outline-2 outline-[#FFCFB1] bg-[#fbfaec] shadow rounded relative flex gap-y-1 gap-x-2"
    class:next-expansion={next_expansion && controllers.show_next_expansion}
    class:bounce={next_expansion && !expand && controllers.show_next_expansion}
    class:end={isEnd}
    class:on-max-value-path={on_max_value_path &&
      controllers.show_max_value_path}
  >
    <div class="flex flex-col grow px-2 gap-y-2">
      <div class="text-[1.3rem] font-mono text-orange-900 flex items-center">
        <span class="card-label mr-2 capitalize select-none" class:end={isEnd}
          >{task.label}</span
        >
        {#if !isEnd}
          <button
            class="shrink-0 ml-auto cursor-pointer hover:bg-orange-300 p-0.5 rounded"
            onclick={() => handleToggleExpand(task[id_key])}
            ><img src="panel_top_open.svg" alt="more" class="w-6 h-6" /></button
          >
        {/if}
      </div>
      {#if !isEnd && expand}
        <div
          in:slide
          class="border-t border-gray-300 flex flex-col min-w-[15rem]"
        >
          <div class="text-sm text-gray-400 italic">Description</div>
          {task.description}
        </div>
        <div in:slide class=" border-gray-300 flex gap-x-2 min-w-[15rem]">
          <div class="text-sm text-gray-400 italic">Confidence</div>
          <div class="text-sm">
            {task.confidence?.toFixed(2)}
          </div>
        </div>
        <div in:slide class=" border-gray-300 flex gap-x-2 min-w-[15rem]">
          <div class="text-sm text-gray-400 italic">Complexity</div>
          <div class="text-sm">
            {task.complexity?.toFixed(2)}
          </div>
        </div>
        <div class="flex gap-x-2 mt-1">
          <div class="flex justify-between flex-wrap">
            <button
              class="action-button outline-gray-200 bg-gray-100 hover:bg-green-100"
              class:disabled={task.sub_tasks === undefined ||
                task.sub_tasks.length === 0}
              class:active={show_subtasks}
              onclick={() => showSubTasks()}>SubTasks</button
            >
          </div>
        </div>
        <div in:slide class="more-actions flex flex-wrap mb-2">
          <div class="flex gap-x-2">
            <button
              class="action-button rounded outline-2 outline-orange-200 bg-orange-100 hover:bg-orange-200"
              onclick={() => handleDecompose(task)}>Decompose</button
            >
            <button
              class="action-button rounded outline-2 outline-gray-200 bg-gray-100 hover:bg-gray-200"
              >Edit</button
            >
            <button
              class="action-button rounded outline-2 outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              onclick={() => handleDeleteTask(task)}
            >
              Delete
            </button>
            <button
              class="action-button rounded outline-2 outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              tabindex="0"
              onclick={() => handleDeleteSubTasks(task)}
            >
              Delete SubTasks
            </button>
          </div>
        </div>
      {/if}
    </div>
    {#if expand}
      <div class="flex bg-[#fbfaec] border-y border-r border-gray-200">
        <div in:slide class="mt-1 flex flex-col">
          <img
            src="bot.svg"
            alt="bot"
            class="mx-2 w-7 h-7 inline-block p-0.5 border-r border-b border-gray-300 shadow min-w-[15rem] bg-gray-50"
          />
          <div class="text-sm text-gray-400 italic mx-2">Explanation</div>
          <span class="mx-2 overflow-auto">
            {task.explanation}
          </span>
        </div>
      </div>
    {/if}
  </div>
  {#if !expand}
    <div
      in:slide
      class="more-actions hidden flex-wrap absolute top-[100%] left-1/2 -translate-x-1/2"
      class:bounce={next_expansion && !expand}
    >
      <div class="flex gap-x-0">
        <button
          class="action-button border-y-2 border-l-2 border-r-2 border-dashed border-orange-500 bg-[#fbfaec] hover:bg-orange-200 ml-auto right-0"
          tabindex="0"
          onclick={() => handleSetAsNextExpansion(task)}
        >
          Next Expansion
        </button>
        <button
          class="action-button border-y-2 border-l-2 border-r-1 border-orange-200 bg-orange-100 hover:bg-orange-200"
          onclick={() => handleDecompose(task)}>Decompose</button
        >
        <button
          class="action-button border-y-2 border-x-1 border-gray-200 bg-gray-100 hover:bg-gray-200"
          >Edit</button
        >
        <button
          class="action-button border-y-2 border-x-1 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
          onclick={() => handleDeleteTask(task)}
        >
          Delete
        </button>
        <button
          class="action-button border-y-2 border-l-1 border-r-2 border-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
          tabindex="0"
          onclick={() => handleDeleteSubTasks(task)}
        >
          Delete SubTasks
        </button>
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "../app.css";
  .on-max-value-path {
    @apply border-black border-3 outline-none;
  }
  .card-label.end {
    @apply flex justify-center items-center;
  }
  .end {
    @apply min-w-[5rem] flex items-center justify-center;
  }
  .next-expansion {
    @apply outline-3 outline-orange-500 outline-dashed shadow-none;
  }
  .bounce {
    @apply animate-bounce;
  }
  .container:hover .next-expansion,
  .container:hover .more-actions {
    animation-play-state: paused;
  }

  .container:hover > .more-actions {
    @apply flex flex-wrap;
  }
  .action-button {
    @apply px-1 py-0.5 text-sm font-mono;
  }
  .disabled {
    @apply cursor-not-allowed bg-gray-300 outline-gray-200 opacity-50;
  }
  .active {
    @apply outline-gray-600 bg-green-200;
  }
  .task-card {
    transition:
      width 0.3s ease,
      height 0.3s ease;
  }
  :global(.new-node) {
    & .task-card {
      @apply bg-orange-200;
    }
  }
</style>
