<script lang="ts">
  import type { tControllers, tSemanticTask } from "types";
  import type { Snippet } from "svelte";
  import { getContext } from "svelte";
  import { slide, scale } from "svelte/transition";
  import EvaluationIndicator from "./EvaluationIndicator.svelte";
  import { evaluation_colors } from "constants";
  import SemanticTaskCardUtilities from "./SemanticTaskCardUtilities.svelte";
  let {
    task = $bindable(),
    id_key,
    next_expansion,
    on_max_value_path = false,
    controllers,
    streaming,
    show_explanation = $bindable(false),
    expand,
    handleTaskHovered = () => {},
    handleSetAsNextExpansion = () => {},
    handleDecompose = () => {},
    handleToggleExplain = () => {},
    handleToggleExpand = () => {},
    handleToggleShowSubTasks = () => {},
    handleDeleteSubTasks = () => {},
    handleDeleteTask = () => {},
    complexity_icon,
    coherence_icon,
    importance_icon,
  }: {
    task: tSemanticTask;
    id_key: string;
    next_expansion: boolean;
    on_max_value_path: boolean;
    controllers: tControllers;
    streaming: boolean;
    show_explanation: boolean;
    expand: boolean;
    handleTaskHovered: Function;
    handleSetAsNextExpansion?: Function;
    handleDecompose?: Function;
    handleToggleExplain?: Function;
    handleToggleExpand?: Function;
    handleToggleShowSubTasks?: Function;
    handleDeleteSubTasks?: Function;
    handleDeleteTask?: Function;
    complexity_icon: Snippet;
    coherence_icon: Snippet;
    importance_icon: Snippet;
  } = $props();
  let show_subtasks = $state(false);
  let show_actions = $state(false);
  function showSubTasks() {
    show_subtasks = !show_subtasks;
    handleToggleShowSubTasks(task[id_key]);
  }
  let isEnd = $derived(task.label === "END");
  const handleUserFeedback: Function = getContext("handleUserFeedback");
  $inspect(task);
</script>

<div
  role="tooltip"
  class="container flex flex-col w-min rounded-sm items-center gap-y-0.5"
  class:card-disabled={streaming}
  onmouseover={() => {
    if (!expand) handleTaskHovered(task[id_key], true);
  }}
  onmouseout={() => {
    if (!expand) handleTaskHovered(task[id_key], false);
  }}
  onfocus={() => {
    if (!expand) handleTaskHovered(task[id_key], true);
  }}
  onblur={() => {
    if (!expand) handleTaskHovered(task[id_key], false);
  }}
>
  <div
    class="task-card text-slate-600 w-min min-w-[18rem] transition-all outline-2 outline-[#FFCFB1] bg-[#fbfaec] shadow rounded relative flex gap-y-1 gap-x-2"
    class:next-expansion={next_expansion && controllers.show_next_expansion}
    class:bounce={next_expansion && !expand && controllers.show_next_expansion}
    class:end={isEnd}
    class:on-max-value-path={on_max_value_path &&
      controllers.show_max_value_path}
    class:not-expand={!expand}
  >
    <div class="flex flex-col grow">
      <div
        class="header-container relateive text-[1.3rem] font-mono text-orange-900 flex items-center px-2 border-gray-300"
        style={`border-bottom: ${expand ? "1px solid lightgray" : "unset"}`}
      >
        <span class="card-label mr-2 capitalize select-none" class:end={isEnd}
          >{task.label}</span
        >
        {#if !expand}
          <div class="absolute left-0 bottom-[calc(100%+5px)] flex gap-x-1">
            {#if controllers.show_complexity}
              <div transition:scale class="flex">
                <EvaluationIndicator
                  {streaming}
                  show_transition={true}
                  value={task.user_evaluation.complexity}
                  label="Complexity"
                  icon={complexity_icon}
                  handleToggle={(user_value) =>
                    handleUserFeedback(task[id_key], "complexity", user_value)}
                />
              </div>
            {/if}
            {#if controllers.show_coherence}
              <div transition:scale class="flex">
                <EvaluationIndicator
                  {streaming}
                  show_transition={true}
                  value={task.user_evaluation.coherence}
                  label="Coherence"
                  icon={coherence_icon}
                  handleToggle={(user_value) =>
                    handleUserFeedback(task[id_key], "coherence", user_value)}
                />
              </div>
            {/if}
            {#if controllers.show_importance}
              <div transition:scale class="flex">
                <EvaluationIndicator
                  {streaming}
                  show_transition={true}
                  value={task.user_evaluation.importance}
                  label="Importance"
                  icon={importance_icon}
                  handleToggle={(user_value) =>
                    handleUserFeedback(task[id_key], "importance", user_value)}
                />
              </div>
            {/if}
          </div>
        {/if}
        {#if !isEnd}
          <button
            class="shrink-0 ml-auto cursor-pointer hover:bg-orange-300 p-0.5 rounded"
            style={`visibility: ${streaming ? "hidden" : "visible"}`}
            onclick={() => handleToggleExpand(task[id_key])}
            ><img src="panel_top_open.svg" alt="more" class="w-6 h-6" /></button
          >
        {/if}
      </div>
      <div class="flex flex-col px-2 gap-y-1">
        {#if !isEnd && expand}
          <div in:slide class="flex flex-col min-w-[15rem]">
            <div class="text-sm text-gray-400 italic">Description</div>
            {task.description}
          </div>
          <div in:slide class="flex gap-x-1 min-w-[15rem] items-center">
            <EvaluationIndicator
              {streaming}
              show_transition={false}
              value={task.user_evaluation.complexity}
              label="Complexity"
              icon={complexity_icon}
              handleToggle={(user_value) =>
                handleUserFeedback(task[id_key], "complexity", user_value)}
            />
            <div class="text-sm text-gray-500 italic w-[5rem]">Complexity</div>
            <div class="text-sm">
              {task.user_evaluation.complexity ? "Good" : "Bad"}
            </div>
          </div>
          <div in:slide class="flex gap-x-1 min-w-[15rem] items-center">
            <EvaluationIndicator
              {streaming}
              value={task.user_evaluation.coherence}
              show_transition={false}
              label="Coherence"
              icon={coherence_icon}
              handleToggle={(user_value) =>
                handleUserFeedback(task[id_key], "coherence", user_value)}
            />
            <div class="text-sm text-gray-500 italic w-[5rem]">Coherence</div>
            <div class="text-sm">
              {task.user_evaluation.coherence ? "Good" : "Bad"}
            </div>
          </div>
          <div in:slide class="flex gap-x-1 min-w-[15rem] items-center">
            <EvaluationIndicator
              {streaming}
              show_transition={false}
              value={task.user_evaluation.importance}
              label="Importance"
              icon={importance_icon}
              handleToggle={(user_value) =>
                handleUserFeedback(task[id_key], "importance", user_value)}
            />
            <div class="text-sm text-gray-500 italic w-[5rem]">Importance</div>
            <div class="text-sm">
              {task.user_evaluation.importance ? "Good" : "Bad"}
            </div>
          </div>
          <div class="flex gap-x-2 my-1">
            <div class="flex justify-between flex-wrap">
              <!-- <button
                class="action-button outline-gray-200 bg-gray-100 hover:bg-green-100"
                class:disabled={task.sub_tasks === undefined ||
                  task.sub_tasks.length === 0}
                class:active={show_subtasks}
                onclick={() => showSubTasks()}>SubTasks</button
              > -->
            </div>
          </div>
          <div in:slide class="more-actions flex flex-wrap mb-2">
            <SemanticTaskCardUtilities
              {task}
              {handleDecompose}
              {handleDeleteTask}
              {handleDeleteSubTasks}
              {handleSetAsNextExpansion}
            />
          </div>
        {/if}
      </div>
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
      class="more-actions hidden absolute top-[calc(100%+3px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
      class:bounce={next_expansion && !expand}
    >
      <SemanticTaskCardUtilities
        {task}
        {handleDecompose}
        {handleDeleteTask}
        {handleDeleteSubTasks}
        {handleSetAsNextExpansion}
      />
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "../app.css";
  .card-disabled {
    @apply cursor-not-allowed pointer-events-none;
  }
  .card-label.end {
    @apply flex justify-center items-center;
  }
  .end {
    @apply min-w-[5rem] flex items-center justify-center;
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
    @apply cursor-not-allowed pointer-events-none  outline-gray-200 opacity-50;
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
    & .task-card.not-expand {
      @apply bg-orange-200;
    }
    & .header-container {
      @apply bg-orange-200;
    }
  }
  :global(.on-hovered-path) {
    & .task-card {
      @apply outline-black outline-4 border-none rounded-none shadow-md;
      & .card-label {
        @apply font-bold;
      }
    }
  }
  .on-max-value-path {
    @apply outline-black outline-4 border-none rounded-none shadow-md;
    & .card-label {
      @apply font-bold;
    }
  }

  .next-expansion {
    @apply outline-3 outline-orange-500 outline-dashed shadow-none;
  }
</style>
