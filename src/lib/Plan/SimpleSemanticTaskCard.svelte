<script lang="ts">
  import type { tSemanticTask } from "types";
  import { slide, scale } from "svelte/transition";
  import EvaluationIndicator from "../Searching/EvaluationIndicator.svelte";
  import { custom_confirm } from "lib/customConfirm";
  import { trim } from "lib/trim";
  import { semanticTaskPlanState } from "lib/ExecutionStates.svelte";
  let {
    task,
    task_options,
    expand,
    handleDecompose = () => {},
    handleToggleExpand = () => {},
    handleToggleShowSubTasks = () => {},
    handleDeleteSubTasks = () => {},
    handleDeleteTask = () => {},
    handleAddParent = () => {},
  }: {
    task: tSemanticTask;
    task_options: [string, string][];
    expand: boolean;
    handleDecompose?: Function;
    handleToggleExpand?: Function;
    handleToggleShowSubTasks?: Function;
    handleDeleteSubTasks?: Function;
    handleDeleteTask?: Function;
    handleAddParent: Function;
  } = $props();
  let show_subtasks = $state(false);
  let adding_parent = $state(false);
  let isRoot = $derived(task.id === "-1");
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

{#if isRoot}
  <div
    class="container task-card text-slate-600 w-min min-w-[5rem] pb-1 transition-all outline-2 outline-[#FFCFB1] bg-[#fbfaec] shadow rounded relative flex justify-center"
  >
    <div
      class="font-mono text-orange-900 border-gray-300 text-[1.2rem] italic flex items-center justify-center"
    >
      <span class="card-label capitalize mt-1 select-none">{task.label}</span>
    </div>
  </div>
{:else}
  <div
    class="container task-card text-slate-600 w-min min-w-[18rem] pb-1 transition-all outline-2 outline-[#FFCFB1] bg-[#fbfaec] shadow rounded relative flex gap-y-1 gap-x-2"
  >
    <div class="flex flex-col grow px-2 gap-y-2">
      <div
        class="font-mono text-orange-900 border-gray-300 text-[1.2rem] italic flex items-center"
        style={`border-bottom: ${expand ? "1px solid lightgray" : "unset"}`}
      >
        <span
          class="card-label mr-2 capitalize mt-1"
          use:trim
          contenteditable
          onblur={(e) => {
            const new_task = JSON.parse(JSON.stringify(task));
            new_task.label = (e.target as HTMLElement).innerText.trim();
            semanticTaskPlanState.updateSemanticTask(task.id, new_task);
          }}>{task.label}</span
        >
        <button
          class="shrink-0 ml-auto cursor-pointer hover:bg-orange-300 p-0.5 rounded"
          title="Expand/Hide"
          onclick={() => handleToggleExpand(task.id)}
          ><img src="panel_top_open.svg" alt="more" class="w-6 h-6" /></button
        >
      </div>
      {#if expand}
        <div in:slide class=" border-gray-300 flex flex-col min-w-[15rem]">
          <div class="text-sm text-gray-400 italic">Description</div>
          <div
            use:trim
            contenteditable
            onblur={(e) => {
              const new_task = JSON.parse(JSON.stringify(task));
              new_task.description = (e.target as HTMLElement).innerText.trim();
              semanticTaskPlanState.updateSemanticTask(task.id, new_task);
            }}
          >
            {task.description}
          </div>
        </div>
        <div in:slide class="flex gap-x-1 min-w-[15rem] items-center">
          <EvaluationIndicator
            {task}
            show_transition={false}
            value={task.user_evaluation.complexity}
            llm_value={task.llm_evaluation.complexity}
            llm_reasoning={task.llm_evaluation.complexity_reason}
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
            {task}
            value={task.user_evaluation.coherence}
            llm_value={task.llm_evaluation.coherence}
            llm_reasoning={task.llm_evaluation.coherence_reason}
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
            {task}
            show_transition={false}
            value={task.user_evaluation.importance}
            llm_value={task.llm_evaluation.importance}
            llm_reasoning={task.llm_evaluation.importance_reason}
            label="Importance"
            icon={importance_icon}
          />
          <div class="text-sm text-gray-500 italic w-[5rem]">Importance</div>
          <div class="text-sm">
            {task.user_evaluation.importance ? "Good" : "Bad"}
          </div>
        </div>
        <div class="flex gap-x-2 mt-1">
          <div class="flex justify-between flex-wrap"></div>
          <div class="flex gap-x-2 relative grow">
            <div class="more-actions">
              <div class="flex gap-x-2">
                <div class="relative add-parent-container">
                  <button
                    class="action-button outline-gray-200 bg-orange-100 hover:bg-orange-200 relative"
                    onclick={() => (adding_parent = true)}
                  >
                    Add Parent
                  </button>
                  <div
                    class="options absolute hidden top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
                  >
                    <div class="flex flex-col w-max">
                      {#each task_options as option}
                        <button
                          class="text-sm bg-gray-50 outline-2 outline-gray-200 px-1 py-0.5 hover:bg-gray-200"
                          onclick={() => {
                            handleAddParent(option[0]);
                            adding_parent = false;
                          }}
                        >
                          {option[1]}
                        </button>
                      {/each}
                    </div>
                  </div>
                </div>
                <button
                  class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
                  onclick={async () => {
                    const result = await custom_confirm(
                      `Are you sure you want to delete ${task.label}?`
                    );
                    if (result) handleDeleteTask(task);
                  }}
                >
                  <!-- <img src="close.svg" alt="x" /> -->
                  Delete
                </button>
                <!-- <button
                class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
                tabindex="0"
                class:disabled={task.sub_tasks === undefined ||
                  task.sub_tasks.length === 0}
                onclick={() => handleDeleteSubTasks(task)}
              >
                Delete SubTasks
              </button> -->
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
    {#if expand && task.explanation !== "N/A"}
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
          <div class="flex gap-x-2">
            <!-- <button
              class="action-button outline-orange-200 bg-orange-100 hover:bg-orange-200"
              onclick={() => handleDecompose(task)}>Decompose</button
            > -->
            <div class="relative add-parent-container">
              <button
                class="action-button outline-gray-200 bg-orange-100 hover:bg-orange-200 relative"
                onclick={() => (adding_parent = true)}
              >
                Add Parent
              </button>
              <div
                class="options absolute hidden top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
              >
                <div class="flex flex-col w-max">
                  {#each task_options as option}
                    <button
                      class="text-sm bg-gray-50 outline-2 outline-gray-200 px-1 py-0.5 hover:bg-gray-200"
                      onclick={() => {
                        handleAddParent(option[0]);
                        adding_parent = false;
                      }}
                    >
                      {option[1]}
                    </button>
                  {/each}
                </div>
              </div>
            </div>
            <button
              class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              onclick={async () => {
                const result = await custom_confirm(
                  `Are you sure you want to delete ${task.label}?`
                );
                if (result) handleDeleteTask(task);
              }}
            >
              Delete
            </button>
            <!-- <button
              class="action-button outline-red-300 bg-red-200 hover:bg-red-300 ml-auto right-0"
              tabindex="0"
              class:disabled={task.sub_tasks === undefined ||
                task.sub_tasks.length === 0}
              onclick={() => handleDeleteSubTasks(task)}
            >
              Delete SubTasks
            </button> -->
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style lang="postcss">
  @reference "tailwindcss";
  .container:hover > .more-actions {
    @apply flex flex-wrap;
  }
  .action-button {
    @apply outline-2 px-1 py-0.5 text-sm font-mono;
  }
  .task-card {
    transition:
      width 0.3s ease,
      height 0.3s ease;
  }
  .add-parent-container:hover .options {
    @apply block;
  }
</style>
