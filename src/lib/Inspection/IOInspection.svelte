<script lang="ts">
  import { slide } from "svelte/transition";
  import { trim } from "lib/trim";
  let {
    input_key_options,
    state_input_key,
    doc_input_keys,
    state_output_key,
    handleDeleteDocInputKey,
    handleAddDocInputKey,
    handleEditStateOutputKey,
    available_states,
    handleDeleteStateInputKey,
    handleAddStateInputKey,
  } = $props();

  let unselected_state_keys = $derived(
    available_states
      ? Object.keys(available_states).filter((k) => k !== state_input_key)
      : []
  );
</script>

<div in:slide class="format-container flex justify-around divide-x">
  <div class="key-section">
    <div class="option-label">State Input Key</div>
    <div class="option-value relative">
      {state_input_key}
      <button
        class="option-value-delete-icon hidden justify-center items-center absolute top-0 bottom-0 left-0 right-0 bg-gray-200"
        onclick={() => handleDeleteStateInputKey()}
        ><img src="minus.svg" class="w-4 h-4" alt="delete" /></button
      >
    </div>

    <div class="relative flex flex-wrap gap-1 px-1">
      {#if unselected_state_keys.length === 0}
        <div class="w-max px-1 text-gray-600 text-sm italic select-none">
          {available_states ? "All keys are added" : "No available states"}
        </div>
      {:else}
        <div class="text-gray-600 text-sm italic select-none">
          Available Options:
        </div>
        {#each unselected_state_keys as state_key}
          <div
            class="add-key relative text-xs outline-1 outline-gray-300 px-1 font-mono rounded"
          >
            {state_key}
            <button
              class="plus-button absolute left-0 top-0 bottom-0 right-0 bg-gray-50"
              onclick={() => handleAddStateInputKey(state_key)}
            >
              <img
                src="plus_gray.svg"
                alt="add"
                class="w-5 h-5 pointer-events-none"
              />
            </button>
          </div>
        {/each}
      {/if}
    </div>
  </div>
  <div class="key-section">
    <div class="option-label">Doc Input Keys</div>
    {#each doc_input_keys as doc_input_key}
      <div class="option-value relative">
        {doc_input_key}
        <button
          class="option-value-delete-icon hidden justify-center items-center absolute top-0 bottom-0 left-0 right-0 bg-gray-200"
          onclick={() => handleDeleteDocInputKey(doc_input_key)}
          ><img src="minus.svg" class="w-4 h-4" alt="delete" /></button
        >
      </div>
    {/each}

    <div class="relative flex flex-wrap gap-1 px-1">
      {#if input_key_options.length === 0}
        <div class="w-max px-1 text-gray-600 text-sm italic select-none">
          All keys are added
        </div>
      {:else}
        <div class="text-gray-600 text-sm italic select-none">
          Available Options:
        </div>
        {#each input_key_options as existing_key}
          <div
            class="add-key relative text-xs outline-1 outline-gray-300 px-1 font-mono rounded"
          >
            {existing_key}
            <button
              class="plus-button absolute left-0 top-0 bottom-0 right-0 bg-gray-50"
              onclick={() => handleAddDocInputKey(existing_key)}
            >
              <img
                src="plus_gray.svg"
                alt="add"
                class="w-5 h-5 pointer-events-none"
              />
            </button>
          </div>
        {/each}
      {/if}
    </div>
  </div>
  <div class="key-section relative">
    <div class="option-label">State Output Key</div>
    <div class="option flex justify-center relative w-full">
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="key-input outline-1 outline-gray-300 rounded px-2 flex justify-center font-mono text-xs focus:outline-blue-400 focus:rounded-none"
        contenteditable
        use:trim
        onblur={(e: any) => {
          const state_output_key = e.target.innerText.trim();
          handleEditStateOutputKey(state_output_key);
        }}
        onkeydown={(e: any) => {
          if (e.key === "Enter") {
            e.preventDefault();
            e.target.blur();
          }
        }}
      >
        {state_output_key}
      </div>
    </div>
  </div>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .option-label {
    @apply text-slate-600 bg-gray-100 w-full flex justify-center font-mono text-sm;
  }
  .option-value {
    @apply outline-1 outline-gray-300 rounded px-2 hover:bg-gray-200 transition-all cursor-pointer flex justify-center font-mono text-xs;
  }
  .option-value:hover > .option-value-delete-icon {
    @apply flex;
  }
  .option:hover > .delete {
    @apply flex;
  }
  .plus-button {
    @apply invisible flex items-center justify-center rounded-full  outline-gray-300 outline-2  p-0.5 cursor-pointer;
  }
  .key-section {
    @apply flex-1 flex flex-col items-center gap-y-2;
  }
  .add-key:hover > .plus-button {
    @apply visible;
  }
  .key-input:empty:before {
    content: "Type Here...";
    cursor: text;
    color: #a3a3a3;
  }
</style>
