<script lang="ts">
  import type { tPrimitiveTask } from "types";
  import { slide } from "svelte/transition";
  import { custom_confirm } from "lib/customConfirm";
  import { trim } from "lib/trim";
  import { primitiveTaskState } from "lib/ExecutionStates.svelte";
  import PrimitiveTaskCardUtilities from "./PrimitiveTaskCardUtilities.svelte";
  let {
    task,
    label_options,
    add_parent_options,
    remove_parent_options,
    expand,
    executable,
    compiling,
    handleAddParent = () => {},
    handleRemoveParent = () => {},
    handleExecute = () => {},
    handleCompile = () => {},
    handleInspectTask = () => {},
    handleDeleteTask = () => {},
    handleToggleExpand = () => {},
  }: {
    task: tPrimitiveTask;
    label_options: { label: string; definition: string }[];
    add_parent_options: [string, string][];
    remove_parent_options: [string, string][];
    expand: boolean;
    executable: boolean;
    compiling: boolean | string | undefined;
    handleAddParent: Function;
    handleRemoveParent: Function;
    handleExecute: (task: tPrimitiveTask) => void;
    handleCompile: Function;
    handleInspectTask: Function;
    handleDeleteTask?: Function;
    handleToggleExpand?: Function;
  } = $props();
  let isRoot = $derived(task.id === "-1");
  let show_label_options = $state(false);
  let card_compiling = $derived(
    compiling !== false && (compiling === undefined || compiling === task.id)
  );
</script>

{#if isRoot}
  <div
    class="container task-card font-mono text-sky-900 w-min min-w-[5rem] pb-1 transition-all outline-2 outline-blue-100 bg-[#F2F8FD] shadow rounded relative flex justify-center gap-y-1 gap-x-2"
  >
    <div class="text-[1.2rem] italic flex items-center">
      <span class="card-label mt-1 capitalize select-none">{task.label}</span>
    </div>
  </div>
{:else}
  <div
    class="container task-card text-slate-600 w-min min-w-[18rem] pb-1 transition-all outline-2 outline-blue-100 bg-[#F2F8FD] shadow rounded relative flex gap-y-1 gap-x-2"
  >
    {#if task.recompile_skip_IO  && !card_compiling}
      <div
        class="absolute bottom-[calc(100%+3px)] left-0 flex items-end gap-x-1 animate-bounce bg-gray-50"
      >
        <img
          src="aperture.svg"
          class="w-4 h-4 aniamte-bounce"
          alt="needs compilation"
          title="needs compilation"
        />
        <span class="text-sm italic text-gray-500">
          Needs Compilation {!task.recompile_skip_IO
            ? "From Scratch"
            : "(Skip I/O enabled)"}
        </span>
      </div>
    {/if}
    {#if card_compiling}
      <div
        class="absolute bottom-[calc(100%+3px)] left-0 flex items-end gap-x-1"
      >
        <img
          src="aperture.svg"
          alt="compiling"
          class="w-5 h-5 animate-spin opacity-80"
        />
        <span class="text-sm animate-pulse italic text-gray-500">
          Compiling...
        </span>
      </div>
    {/if}
    <div class="flex flex-col grow px-2 gap-y-2">
      <div
        class="font-mono text-sky-900 border-b border-gray-300 text-[1.2rem] italic flex items-center relative"
        style={`border-bottom: ${expand ? "1px solid lightgray" : "unset"}`}
      >
        <button
          class="card-label mr-2 mt-1 capitalize relative hover:bg-blue-200 rounded px-2 text-left"
          title="Change Label"
          onclick={(e) => (show_label_options = !show_label_options)}
          >{task.label}
        </button>
        <button
          class="shrink-0 ml-auto cursor-pointer hover:bg-blue-300 p-0.5 rounded"
          title="Expand/Hide"
          onclick={() => handleToggleExpand(task.id)}
          ><img
            src="panel_top_open_blue.svg"
            alt="more"
            class="w-6 h-6"
          /></button
        >
        {#if show_label_options}
          <div
            in:slide
            class="label-options flex flex-col absolute top-[calc(100%+0.4rem)] left-[-0.5rem] right-[-0.5rem] outline-2 outline-gray-200 text-xs text-slate-600 z-10 bg-gray-100"
          >
            {#each label_options.toSorted( (a, b) => a.label.localeCompare(b.label) ) as label_option}
              <button
                class="flex items-center justify-center hover:bg-gray-300"
                title="Select Label"
                onclick={() => {
                  show_label_options = false;
                  const new_task = JSON.parse(JSON.stringify(task));
                  // new_task.label = (e.target as HTMLElement).innerText.trim();
                  new_task.label = label_option.label;
                  new_task.description = label_option.definition;
                  new_task.explanation = "N/A";
                  primitiveTaskState.updatePrimitiveTask(task.id, new_task);
                }}
              >
                {label_option.label}
              </button>
            {/each}
          </div>
        {/if}
      </div>
      {#if expand}
        <div
          in:slide
          class="border-b border-gray-300 flex flex-col min-w-[15rem]"
        >
          <div class="text-sm text-gray-400 italic">Description</div>
          <div
            use:trim
            contenteditable
            onblur={(e: any) => {
              const new_task = JSON.parse(JSON.stringify(task));
              new_task.description = (e.target as HTMLElement).innerText.trim();
              primitiveTaskState.updatePrimitiveTask(task.id, new_task);
              e.target.innerHTML = new_task.description;
            }}
          >
            {task.description}
          </div>
        </div>
        <PrimitiveTaskCardUtilities
          {task}
          {executable}
          {add_parent_options}
          {remove_parent_options}
          {handleAddParent}
          {handleRemoveParent}
          {handleExecute}
          {handleCompile}
          {handleInspectTask}
          {handleDeleteTask}
        ></PrimitiveTaskCardUtilities>
      {/if}
    </div>
    {#if expand && task.explanation !== "N/A"}
      <div
        class="flex absolute left-[100.7%] top-0 bottom-1 bg-white border-y border-r border-gray-200"
      >
        <div in:slide class="relative mt-1 flex flex-col">
          <img
            src="bot.svg"
            alt="bot"
            class="mx-2 w-7 h-7 inline-block p-0.5 border-r border-b border-gray-300 shadow min-w-[15rem]"
          />
          <div class="text-sm text-gray-400 italic mx-2">Explanation</div>
          <span class="mx-2 overflow-auto">
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
        <PrimitiveTaskCardUtilities
          {task}
          {executable}
          {add_parent_options}
          {remove_parent_options}
          {handleAddParent}
          {handleRemoveParent}
          {handleExecute}
          {handleCompile}
          {handleInspectTask}
          {handleDeleteTask}
        ></PrimitiveTaskCardUtilities>
      </div>
    {/if}
  </div>
{/if}

<style lang="postcss">
  @reference "tailwindcss";
  .container:hover > .more-actions {
    @apply flex flex-wrap;
  }

  .task-card {
    transition:
      width 0.3s ease,
      height 0.3s ease;
  }
</style>
