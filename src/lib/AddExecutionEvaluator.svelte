<script lang="ts">
  import { trim } from "lib/trim.js";

  let {
    tasks,
    handleGenerateEvaluator,
  }: { tasks: [string, string][]; handleGenerateEvaluator: Function } =
    $props();
  let selected_task: string | undefined = $state(undefined);
</script>

<div
  class="task-option-container flex gap-x-2 items-center px-2 text-sm text-slate-700"
>
  <div class="">Target:</div>
  <div class="options flex gap-2 flex-wrap text-sm">
    {#each tasks as task}
      <button
        class:selected={selected_task === task[0]}
        class="flex gap-x-2 outline-2 outline-gray-100 px-2 py-0.5 rounded text-slate-400 hover:bg-slate-200 hover:text-slate-700"
        onclick={() => (selected_task = task[0])}
      >
        {task[1]}
      </button>
    {/each}
  </div>
</div>
<div class="flex gap-x-1">
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions, a11y_mouse_events_have_key_events (because of reasons) -->
  <div
    use:trim
    contenteditable
    class="user-description grow text-slate-600 italic px-2 min-h-[3rem] max-h-[6rem] overflow-auto flex flex-wrap outline-1 outline-gray-300 rounded"
    onkeydown={(e: any) => {
      console.log(e.key === "Enter", selected_task !== undefined);
      if (e.key === "Enter" && selected_task !== undefined) {
        const text = e.target.innerText;
        handleGenerateEvaluator(text, selected_task);
        e.target.innerText = "";
      }
    }}
  ></div>
  <button
    class="ml-auto shrink-0 w-[4rem] flex justify-center items-center bg-gray-100 hover:outline outline-1 outline-gray-300 rounded px-2 py-1 hover:bg-green-200"
    class:disabled={!selected_task}
    onclick={() => {
      const input_box = document.querySelector(
        ".user-description"
      ) as HTMLElement;
      const text = input_box.innerText;
      if (text) {
        handleGenerateEvaluator(text, selected_task);
        input_box.innerText = "";
      }
    }}
  >
    <img src="send.svg" class="w-6 h-6" alt="send" />
  </button>
</div>

<style lang="postcss">
  @reference "../app.css";
  .disabled {
    @apply pointer-events-none opacity-50;
  }

  .user-description:empty:before {
    content: "Describe what you want to evaluate.";
    color: gray;
    pointer-events: none;
  }
  .selected {
    @apply bg-slate-200 text-slate-700;
  }
</style>
