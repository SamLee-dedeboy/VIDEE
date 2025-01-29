<script lang="ts">
  import type { tSemanticTask } from "types";
  let {
    semantic_tasks,
    handleDecomposeGoal,
  }: { semantic_tasks: tSemanticTask[]; handleDecomposeGoal: Function } =
    $props();
  let task_id_to_label = $derived(
    semantic_tasks.reduce((acc, task) => {
      acc[task.id] = task.label;
      return acc;
    }, {})
  );
</script>

<div
  class="flex flex-col gap-y-2 p-2 outline outline-1 outline-gray-200 shadow rounded relative"
>
  <div class="flex gap-x-2">
    <div
      class="goal-input outline outline-1 outline-gray-400 rounded shadow-md min-h-[5rem] max-h-[8rem] overflow-y-auto px-1 py-0.5"
      contenteditable
    >
      I need to construct a knowledge graph from a collection of documents from
      wikipedia.
    </div>
    <button
      class="outline outline-2 outline-green-300 bg-green-100 hover:bg-green-200 rounded px-2"
      onclick={() => {
        const goal = document.querySelector(".goal-input")?.textContent || "";
        handleDecomposeGoal(goal);
      }}>Decompose</button
    >
  </div>
  <div class="grow h-1 overflow-auto flex flex-col gap-y-1 divide-y pr-3">
    <div class="flex">
      <img src="bot.svg" class="w-6 h-6" alt="bot" />
      <span>Here are the recommended steps: </span>
    </div>
    {#each semantic_tasks as task, index}
      <div class="">
        <div class="border-b border-gray-300 bg-slate-100">
          {index + 1}. {task.label}
        </div>
        <div class="flex flex-col">
          <div class="flex divide-x text-sm">
            <div class="min-w-[13rem] flex flex-col px-1">
              <span class="text-sm italic text-gray-500 self-center"
                >Description</span
              >
              <span>
                {task.description}
              </span>
            </div>
            <div class="flex flex-col px-1">
              <span class="text-sm italic text-gray-500 self-center"
                >Explanation</span
              >
              <span>
                {task.explanation}
              </span>
            </div>
          </div>
        </div>
        <div class="min-w-[10rem] flex px-0.5 gap-x-3 border-t border-gray-200">
          <span class="text-sm italic text-gray-500">Dependencies</span>
          <div class="text-sm flex flex-col justify-center italic">
            {#if task.parentIds.length === 0}
              N/A
            {:else}
              {#each task.parentIds as parentId}
                <span class="">{task_id_to_label[parentId]}</span>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>
