<script lang="ts">
  import type { tSemanticTask } from "types";

  let {
    adding_child_for,
    handleAddChild,
    handleCancel,
  }: {
    adding_child_for: tSemanticTask;
    handleAddChild: Function;
    handleCancel: Function;
  } = $props();
</script>

<div class="flex flex-col gap-y-2 grow">
  <div class="text-gray-600">
    Adding Child for
    <span class="italic text-gray-600 underline font-semibold">
      {adding_child_for.label}
    </span>
  </div>
  <div class="flex gap-x-2 text-sm items-center">
    <div class=" text-gray-600 italic">Name:</div>
    <div
      class="new-node-name grow outline-1 outline-gray-300 rounded p-1"
      contenteditable={true}
    ></div>
  </div>
  <div class="flex flex-col gap-y-1 text-sm">
    <div class="text-gray-600 italic">Description:</div>
    <div
      class="new-node-description grow outline-1 outline-gray-300 rounded min-h-[3rem] p-2"
      contenteditable={true}
    ></div>
  </div>
  <div class="flex justify-between mt-auto bottom-0 text-sm">
    <button
      class="bg-green-100 hover:bg-green-200 outline-2 outline-green-300 rounded px-1 py-0.5 text-slate-600"
      onclick={() => {
        const name = document.querySelector(".new-node-name")!.textContent;
        const description = document.querySelector(
          ".new-node-description"
        )!.textContent;
        handleAddChild(name, description, adding_child_for);
      }}>Confirm</button
    >
    <button
      class="bg-red-100 hover:bg-red-200 outline-2 outline-red-200 rounded px-1 py-0.5 text-slate-600"
      onclick={() => handleCancel()}>Cancel</button
    >
  </div>
</div>
