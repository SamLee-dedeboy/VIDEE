<script lang="ts">
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
  } from "types";
  import { slide } from "svelte/transition";
  import { onMount } from "svelte";
  let {
    task,
  }: {
    task: tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>;
  } = $props();
  let show_description = $state(false);
  let show_formats = $state(false);
  let show_execution = $state(false);
  let show_result = $state(false);
  onMount(() => {
    console.log({ task });
  });
</script>

<div class="flex flex-col px-1">
  <div
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-[#f2f8fd] flex justify-center"
  >
    Inspection
  </div>
  {#if task}
    <div class="flex flex-col px-2 gap-y-1">
      <div class="flex flex-col">
        <div
          role="button"
          tabindex="0"
          class="header-2"
          onclick={() => {
            show_description = !show_description;
          }}
        >
          {task.label}
          <img
            src="chevron_down.svg"
            alt="expand"
            class="hidden ml-auto w-5 h-5"
          />
        </div>
        {#if show_description}
          <div in:slide class="flex flex-col divide-y">
            <div class="flex">
              <!-- <div class="flex shrink-0 px-2 mt-1">
              <img src="info.svg" alt="info" class="w-7 h-7" />
            </div> -->
              <div class="px-1">
                <span class="text-sm text-gray-500">Description - </span>
                {task.description}
              </div>
            </div>
            <div class="flex">
              <div class="shrink-0 px-2">
                <img src="bot.svg" alt="bot" class="w-7 h-7" />
              </div>
              <div>{task.explanation}</div>
            </div>
          </div>
        {/if}
      </div>
      <div class="flex flex-col gap-y-1">
        <div class="flex flex-col">
          <div
            class="header-2"
            role="button"
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
          </div>
          {#if task.doc_input_keys}
            {#if show_formats}
              <div in:slide class="flex justify-around divide-x">
                <div class="key-section">
                  <div class="option-label">State Input Key</div>
                  <div class="option-value">
                    {task.state_input_key}
                  </div>
                  <div class="plus-button">
                    <img src="plus_gray.svg" alt="add" class="w-5 h-5" />
                  </div>
                </div>
                <div class="key-section">
                  <div class="option-label">Doc Input Keys</div>
                  {#each task.doc_input_keys as doc_input_key}
                    <div class="option-value">{doc_input_key}</div>
                  {/each}
                  <div class="plus-button">
                    <img src="plus_gray.svg" alt="add" class="w-5 h-5" />
                  </div>
                </div>
                <div class="key-section relative">
                  <div class="option-label">State Output Key</div>
                  <div class="option flex justify-center relative w-full">
                    <div class="option-value relative">
                      {task.state_output_key}
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
          {:else}
            <div>Needs Compilation...</div>
          {/if}
        </div>
        <div
          role="button"
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
        </div>
        {#if task.execution}
          {#if show_execution}
            <div
              in:slide
              class="flex flex-col divide-y divide-gray-400 divide-dashed pb-2 px-1"
            >
              <div class="flex gap-x-2 items-center py-1">
                <div class="text-gray-700">Execution Method -</div>
                <div class="option-value">{task.execution.tool}</div>
              </div>
              <div class="flex flex-col gap-y-2">
                <div class="text-gray-700">Parameters</div>
                {#each Object.entries(task.execution.parameters) as [key, value]}
                  {#if key === "api_key"}
                    <div></div>
                  {:else if key === "prompt_template"}
                    <div
                      class="flex flex-col border-x-2 border-t-2 border-dashed border-blue-300 shadow"
                    >
                      <div
                        class="flex text-slate-500 justify-center font-mono text-lg bg-blue-50 border-b border-gray-300"
                      >
                        Prompt Template
                      </div>
                      <div class="flex">
                        {#each value as prompt_template_message}
                          {#if prompt_template_message.role === "system"}
                            <div
                              class="flex flex-[2_2_0%] flex-col gap-x-2 divide-x"
                            >
                              <div
                                class="flex justify-center bg-blue-100 font-mono"
                              >
                                System Instruction
                              </div>
                              <div
                                class="bg-blue-50 px-1 whitespace-pre-line max-h-[20rem] overflow-y-auto"
                              >
                                {prompt_template_message.content}
                              </div>
                            </div>
                          {:else if prompt_template_message.role === "human"}
                            <div class="flex flex-1 flex-col gap-x-2 divide-x">
                              <div
                                class="flex justify-center bg-orange-100 font-mono"
                              >
                                Input Data
                              </div>
                              <div
                                class="bg-orange-50 grow px-1 whitespace-pre-line"
                              >
                                {prompt_template_message.content}
                              </div>
                            </div>
                          {/if}
                        {/each}
                      </div>
                    </div>
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
        {:else}
          <div>Needs Compilation...</div>
        {/if}
      </div>
      {#if true}
        <div class="flex flex-col">
          <div
            role="button"
            tabindex="0"
            class="header-2"
            onclick={() => (show_result = !show_result)}
          >
            Result
            <img
              src="chevron_down.svg"
              alt="expand"
              class="hidden ml-auto w-5 h-5"
            />
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style lang="postcss">
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 bg-blue-100 px-1 cursor-pointer hover:bg-blue-200 flex items-center;
  }
  .header-2:hover > img {
    @apply block;
  }
  .option-label {
    @apply text-slate-600 bg-gray-200 w-full flex justify-center font-mono;
  }
  .option-value {
    @apply outline outline-1 outline-gray-300 rounded px-2 hover:bg-gray-200 transition-all cursor-pointer flex justify-center font-mono;
  }
  .option:hover > .delete {
    @apply flex;
  }
  .plus-button {
    @apply invisible flex rounded-full outline outline-gray-300 outline-2 hover:bg-gray-300 hover:outline-gray-400 p-0.5 cursor-pointer;
  }
  .key-section {
    @apply flex-1 flex flex-col items-center gap-y-2;
  }
  .key-section:hover > .plus-button {
    @apply visible;
  }
</style>
