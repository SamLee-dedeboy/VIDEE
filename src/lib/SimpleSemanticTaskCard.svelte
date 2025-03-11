<script lang="ts">
  import type { tSemanticTask } from "types";
  import { slide, scale } from "svelte/transition";
  import EvaluationIndicator from "./EvaluationIndicator.svelte";
  let {
    task,
    expand,
    handleDecompose = () => {},
    handleToggleExpand = () => {},
    handleToggleShowSubTasks = () => {},
    handleDeleteSubTasks = () => {},
    handleDeleteTask = () => {},
  }: {
    task: tSemanticTask;
    expand: boolean;
    handleDecompose?: Function;
    handleToggleExpand?: Function;
    handleToggleShowSubTasks?: Function;
    handleDeleteSubTasks?: Function;
    handleDeleteTask?: Function;
  } = $props();
  let show_subtasks = $state(false);
  function showSubTasks() {
    show_subtasks = !show_subtasks;
    handleToggleShowSubTasks(task.id);
  }
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

<div
  class="container task-card text-slate-600 w-min min-w-[18rem] pb-1 transition-all outline-2 outline-[#FFCFB1] bg-[#fbfaec] shadow rounded relative flex gap-y-1 gap-x-2"
>
  <div class="flex flex-col grow px-2 gap-y-2">
    <div
      class=" border-gray-300 text-[1.2rem] italic flex items-center"
      style={`border-bottom: ${expand ? "1px solid lightgray" : "unset"}`}
    >
      <span class="card-label mr-2 capitalize">{task.label}</span>
      <button
        class="shrink-0 ml-auto cursor-pointer hover:bg-orange-300 p-0.5 rounded"
        onclick={() => handleToggleExpand(task.id)}
        ><img src="panel_top_open.svg" alt="more" class="w-6 h-6" /></button
      >
    </div>
    {#if expand}
      <div in:slide class=" border-gray-300 flex flex-col min-w-[15rem]">
        <div class="text-sm text-gray-400 italic">Description</div>
        {task.description}
      </div>
      <div in:slide class="flex gap-x-1 min-w-[15rem] items-center">
        <EvaluationIndicator
          show_transition={false}
          value={task.user_evaluation.complexity}
          label="Complexity"
          icon={complexity_icon}
        />
        <div class="text-sm text-gray-500 italic w-[5rem]">Complexity</div>
        <div class="text-sm">
          {task.user_evaluation.complexity ? "Good" : "Bad"}
        </div>
      </div>
      <div in:slide class="flex gap-x-1 min-w-[15rem] items-center">
        <EvaluationIndicator
          value={task.user_evaluation.coherence}
          show_transition={false}
          label="Coherence"
          icon={coherence_icon}
        />
        <div class="text-sm text-gray-500 italic w-[5rem]">Coherence</div>
        <div class="text-sm">
          {task.user_evaluation.coherence ? "Good" : "Bad"}
        </div>
      </div>
      <div in:slide class="flex gap-x-1 min-w-[15rem] items-center">
        <EvaluationIndicator
          show_transition={false}
          value={task.user_evaluation.importance}
          label="Importance"
          icon={importance_icon}
        />
        <div class="text-sm text-gray-500 italic w-[5rem]">Importance</div>
        <div class="text-sm">
          {task.user_evaluation.importance ? "Good" : "Bad"}
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
        <div class="flex gap-x-2 relative grow">
          <div class="more-actions">
            <div class="flex gap-x-2">
              <button
                class="action-button outline-orange-200 bg-orange-100 hover:bg-orange-200"
                onclick={() => handleDecompose(task)}>Decompose</button
              >
              <button
                class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
                onclick={() => handleDeleteTask(task)}
              >
                <!-- <img src="close.svg" alt="x" /> -->
                Delete
              </button>
              <button
                class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
                tabindex="0"
                class:disabled={task.sub_tasks === undefined ||
                  task.sub_tasks.length === 0}
                onclick={() => handleDeleteSubTasks(task)}
              >
                <!-- <img src="close.svg" alt="x" /> -->
                Delete SubTasks
              </button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
  {#if expand}
    <div class="flex g-white border-y border-r border-gray-200 overflow-auto">
      <div in:slide class="relative mt-1 flex flex-col">
        <img
          src="bot.svg"
          alt="bot"
          class="mx-2 w-7 h-7 inline-block p-0.5 border-r border-b border-gray-300 shadow min-w-[15rem] bg-gray-50"
        />
        <div class="text-sm text-gray-400 italic mx-2">Explanation</div>
        <span class="mx-2">
          {task.explanation}
        </span>
      </div>
    </div>
  {/if}
  {#if !expand}
    <div
      in:slide
      class="more-actions hidden absolute top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
    >
      <div class="flex gap-x-0 relative grow">
        <div class="more-actions">
          <div class="flex gap-x-2">
            <button
              class="action-button outline-orange-200 bg-orange-100 hover:bg-orange-200"
              onclick={() => handleDecompose(task)}>Decompose</button
            >
            <button
              class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              onclick={() => handleDeleteTask(task)}
            >
              <!-- <img src="close.svg" alt="x" /> -->
              Delete
            </button>
            <button
              class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              tabindex="0"
              class:disabled={task.sub_tasks === undefined ||
                task.sub_tasks.length === 0}
              onclick={() => handleDeleteSubTasks(task)}
            >
              <!-- <img src="close.svg" alt="x" /> -->
              Delete SubTasks
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "../app.css";
  .container:hover > .more-actions {
    @apply flex flex-wrap;
  }
  .action-button {
    @apply outline-2 px-1 py-0.5 text-sm font-mono;
  }
  .showing-actions {
    @apply bg-green-300 outline-gray-500;
  }
  .disabled {
    @apply cursor-not-allowed pointer-events-none bg-gray-300 outline-gray-200 opacity-50;
  }
  .active {
    @apply outline-gray-600 bg-green-200;
  }
  .task-card {
    transition:
      width 0.3s ease,
      height 0.3s ease;
  }
  .task-card:hover {
    & .close-button {
      @apply block;
    }
  }
</style>
