<script lang="ts">
  import { slide } from "svelte/transition";
  import PromptTemplate from "./PromptTemplate.svelte";
  import { trim } from "lib/trim";
  import type { tExecutionEvaluator } from "types";
  import DocumentCard from "./DocumentCard.svelte";
  let {
    evaluator = $bindable(),
  }: {
    evaluator: tExecutionEvaluator;
  } = $props();
  let show_parameters = $state(false);
  let show_description = $state(true);
  let show_formats = $state(false);
  let show_execution = $state(false);
  let show_result = $state(false);

  let result = $state(undefined);
  function handleFetchEvaluationResult() {}
</script>

<div class="flex flex-col px-1 gap-y-2">
  <div
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-emerald-100 flex justify-center"
  >
    {evaluator.name}
  </div>
  <div class="flex flex-col px-2 gap-y-1">
    <div class="flex flex-col">
      <button
        tabindex="0"
        class="header-2"
        onclick={() => {
          show_description = !show_description;
        }}
      >
        Description
        <img
          src="chevron_down.svg"
          alt="expand"
          class="hidden ml-auto w-5 h-5"
        />
      </button>
      {#if show_description}
        <div in:slide class="flex flex-col divide-y">
          <div class="flex">
            <div class="px-1">
              <span class="text-sm text-gray-500">Description - </span>
              {evaluator.definition}
            </div>
          </div>
        </div>
      {/if}
    </div>
    <div class="flex flex-col gap-y-1">
      <div class="flex flex-col">
        <button
          class="header-2"
          tabindex="0"
          onclick={() => {
            show_formats = !show_formats;
          }}
        >
          Input/Output Formats
          <img
            src="chevron_down.svg"
            alt="expand"
            class="hidden ml-auto w-5 h-5"
          />
        </button>
        {#if evaluator.doc_input_keys}
          {#if show_formats}
            <div in:slide class="flex justify-around divide-x divide-dashed">
              <div class="key-section">
                <div class="option-label">State Input Key</div>
                <div class="option-value">
                  {evaluator.state_input_key}
                </div>
                <div class="plus-button">
                  <img src="plus_gray.svg" alt="add" class="w-5 h-5" />
                </div>
              </div>
              <div class="key-section">
                <div class="option-label">Doc Input Keys</div>
                {#each evaluator.doc_input_keys as doc_input_key}
                  <div class="option-value">{doc_input_key}</div>
                {/each}
                <div class="plus-button">
                  <img src="plus_gray.svg" alt="add" class="w-5 h-5" />
                </div>
              </div>
              <div class="key-section relative">
                <div class="option-label">State Output Key</div>
                <div class="option flex justify-center relative w-full px-1">
                  <div class="option-value relative">
                    {evaluator.state_output_key}
                  </div>
                  <div
                    class="delete hidden absolute right-0 top-1 bottom-1 items-center cursor-pointer hover:bg-red-200 p-1 rounded-full"
                  >
                    <img src="trash.svg" alt="delete" class="w-5 h-5" />
                  </div>
                </div>
                <div class="plus-button">
                  <img src="plus_gray.svg" alt="add" class="w-5 h-5" />
                </div>
              </div>
            </div>
          {/if}
        {/if}
      </div>
      <button
        tabindex="0"
        class="header-2"
        onclick={() => (show_execution = !show_execution)}
      >
        Execution
        <img
          src="chevron_down.svg"
          alt="expand"
          class="hidden ml-auto w-5 h-5"
        />
      </button>
      {#if evaluator.parameters}
        {#if show_execution}
          <div
            in:slide
            class="flex flex-col divide-y divide-gray-400 divide-dashed pb-2 px-1"
          >
            <div class="flex flex-col gap-y-2">
              <div class="text-gray-700">Parameters</div>
              {#each Object.entries(evaluator.parameters) as [key, value]}
                {#if key === "api_key"}
                  <div></div>
                {:else if key === "prompt_template"}
                  <PromptTemplate
                    messages={value}
                    --bg-color="#f6fffb"
                    --border-color="#00d492"
                  ></PromptTemplate>
                {:else}
                  <div class="flex items-center gap-x-2">
                    <div class="italic text-gray-600 w-[3rem]">{key}</div>
                    <div class="option-value">{value}</div>
                  </div>
                {/if}
              {/each}
            </div>
          </div>
        {/if}
      {/if}
    </div>
    {#if true}
      <div class="flex flex-col">
        <div class="flex flex-col">
          <button
            tabindex="0"
            class="header-2"
            onclick={() => {
              show_result = !show_result;
              handleFetchEvaluationResult();
            }}
          >
            Result
            <img
              src="chevron_down.svg"
              alt="expand"
              class="hidden ml-auto w-5 h-5"
            />
          </button>
        </div>
        {#if show_result && result !== undefined}
          <div in:slide class="flex flex-col">
            {#each Object.keys(result) as state_input_key}
              <div class="flex flex-col">
                <div>{state_input_key}</div>
                <div class="flex flex-wrap gap-2">
                  {#each result[state_input_key] as doc}
                    <DocumentCard
                      document={doc}
                      --bg-color="oklch(0.97 0.014 254.604)"
                      --bg-hover-color="oklch(0.882 0.059 254.128)"
                    />
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 bg-emerald-50 px-1 cursor-pointer hover:bg-emerald-100 flex items-center;
  }
  .header-2:hover > img {
    @apply block;
  }
  .option-label {
    @apply text-slate-600 bg-gray-100 w-full flex justify-center font-mono text-sm;
  }
  .option-value {
    @apply outline-1 outline-gray-300 rounded px-2 hover:bg-gray-200 transition-all cursor-pointer flex justify-center font-mono text-sm;
  }
  .option:hover > .delete {
    @apply flex;
  }
  .plus-button {
    @apply invisible flex rounded-full  outline-gray-300 outline-2 hover:bg-gray-300 hover:outline-gray-400 p-0.5 cursor-pointer;
  }
  .key-section {
    @apply flex-1 flex flex-col items-center gap-y-2;
  }
  .key-section:hover > .plus-button {
    @apply visible;
  }

  .user-input-name:empty:before {
    content: "Name the evaluator...";
    color: gray;
    pointer-events: none;
  }
  .user-input-description:empty:before {
    content: "Describe the evaluation criteria...";
    color: gray;
    pointer-events: none;
  }
  .user-input-name:focus,
  .user-input-description:focus {
    @apply justify-start;
  }
  .exec-evaluator-container:hover {
    & .delete-button {
      @apply flex;
    }
  }
  .disabled {
    @apply cursor-not-allowed opacity-50 outline-none;
  }
  .disabled-button {
    pointer-events: none;
  }
  .selected {
    @apply bg-slate-200 text-slate-700;
  }
</style>
