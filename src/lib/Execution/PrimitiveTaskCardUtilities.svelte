<script lang="ts">
  import { custom_confirm } from "lib/customConfirm";
  let {
    task,
    executable,
    add_parent_options,
    remove_parent_options,
    handleExecute,
    handleCompile,
    handleInspectTask,
    handleDeleteTask,
    handleAddParent,
    handleRemoveParent,
  } = $props();
  let adding_parent = $state(false);
  let removing_parent = $state(false);
  let skip_IO_enabled = $derived(
    task.recompile_needed_parameters && !task.recompile_needed_IO
  );
</script>

<div class="flex gap-x-2">
  <button
    class="action-button outline-gray-200 bg-gray-100 hover:bg-gray-200"
    class:disabled={!executable}
    onclick={() => handleExecute(task)}>Execute</button
  >
  <div class="relative compile-container">
    <button
      class="action-button outline-blue-200 bg-[#eff6ff] hover:bg-blue-100"
      >Compile
    </button>
    <div
      class="options-compile font-mono absolute hidden flex-col divide-y top-[calc(100%+0px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
    >
      <button
        class="bg-[#eff6ff] border-t-2 border-x-2 border-slate-200 hover:bg-gray-200 text-sm px-1 py-0.5"
        class:disabled={!skip_IO_enabled}
        onclick={() =>
          handleCompile(task, true, task.recompile_skip_parameters)}
        >Skip I/O</button
      >
      <button
        class="w-max bg-[#eff6ff] border-b-2 border-x-2 border-slate-200 hover:bg-gray-200 text-sm px-1 py-0.5"
        onclick={() => handleCompile(task)}>From Scratch</button
      >
    </div>
  </div>
  <button
    class="action-button outline-gray-200 bg-blue-200 hover:bg-blue-300"
    onclick={() => handleInspectTask(task)}>Inspect</button
  >
  <div class="relative parent-container">
    <button
      class="action-button outline-blue-200 bg-blue-100 hover:bg-blue-200 relative"
      onclick={() => {
        if (adding_parent) {
          adding_parent = false;
        } else if (removing_parent) {
          removing_parent = false;
        }
      }}
    >
      Parent
    </button>
    <div
      class="options-add-remove hidden absolute flex-nowrap gap-x-1 top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
    >
      <button
        class="bg-green-100 outline-2 outline-green-200 hover:bg-green-200 text-sm px-1 py-0.5"
        onclick={() => (adding_parent = !adding_parent)}>Add</button
      >
      <button
        class="bg-red-100 outline-2 outline-red-200 hover:bg-red-200 text-sm px-1 py-0.5"
        onclick={() => (removing_parent = !removing_parent)}>Remove</button
      >
    </div>
    {#if adding_parent}
      <div
        class="options absolute flex top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
      >
        <div class="flex flex-col w-max">
          {#each add_parent_options as option}
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
    {/if}
    {#if removing_parent}
      <div
        class="options absolute flex top-[calc(100%+1px)] left-1/2 -translate-x-1/2 mt-[-0.5rem] pt-[0.58rem]"
      >
        <div class="flex flex-col w-max">
          {#each remove_parent_options as option}
            <button
              class="text-sm bg-gray-50 outline-2 outline-gray-200 px-1 py-0.5 hover:bg-gray-200"
              onclick={() => {
                handleRemoveParent(option[0]);
                removing_parent = false;
              }}
            >
              {option[1]}
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>
  <button
    class="action-button outline-red-300 bg-red-200 hover:bg-red-300 rounded-full ml-auto right-0"
    onclick={async () => {
      const result = await custom_confirm(
        `Are you sure you want to delete ${task.label}?`
      );
      if (result) handleDeleteTask(task);
    }}
  >
    Delete
  </button>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .action-button {
    @apply outline-2 rounded px-1 py-0.5 text-sm font-mono;
  }
  .disabled {
    @apply cursor-not-allowed pointer-events-none bg-gray-100 outline-gray-200 text-gray-300;
  }
  .parent-container:hover .options-add-remove {
    @apply flex;
  }
  .compile-container:hover .options-compile {
    @apply flex;
  }
</style>
