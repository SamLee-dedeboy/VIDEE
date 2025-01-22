<script lang="ts">
  import type { tElementaryTask } from "types";
  let { task }: { task: tElementaryTask } = $props();
  let expand = $state(true);
</script>

<div
  class="task-card w-min min-w-[16rem] transition-all outline outline-2 outline-gray-100 bg-[#fbfaec] shadow px-2 py-1 rounded relative flex gap-y-1 gap-x-2"
>
  <div class="flex flex-col grow">
    <div
      class="border-b border-gray-300 text-[1.2rem] italic flex items-center"
    >
      <span class="card-label mr-2 capitalize">{task.label}</span>
      <span
        tabindex="0"
        role="button"
        class="ml-auto right-0 mb-0.5 shrink-0 w-7 p-1 self-stretch flex cursor-pointer hover:!bg-gray-200 rounded"
        style:background-color={expand ? "rgb(187 247 208)" : "unset"}
        onclick={() => {
          expand = !expand;
        }}
        onkeyup={() => {}}
      >
        {#if expand}
          <img src="panel_left_close.svg" class="" alt="collapse" />
        {:else}
          <img src="panel_left_open.svg" class="" alt="expand" />
        {/if}
      </span>
    </div>
    {#if expand}
      <ul
        in:slide
        class="border-b border-gray-300 text-gray-800 flex list-disc list-inside min-w-[15rem]"
      >
        <li>
          {task.description}
        </li>
      </ul>
    {/if}
    <div class="flex flex-col justify-between gap-y-2 mt-1">
      <div class="flex gap-x-2">
        <button
          class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
          >Edit</button
        >
        <button
          class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
        >
          <!-- <img src="close.svg" alt="x" /> -->
          Delete
        </button>
      </div>
    </div>
  </div>
</div>

<style lang="postcss">
  .action-button {
    @apply outline outline-2 rounded px-1 py-0.5 text-sm text-gray-800 font-mono;
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
  .task-card:hover {
    & .close-button {
      @apply block;
    }
  }
</style>
