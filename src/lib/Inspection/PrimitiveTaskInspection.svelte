<script lang="ts">
  import type { tPrimitiveTask } from "types";
  import { slide } from "svelte/transition";
  import { onMount, tick } from "svelte";
  import { trim } from "lib/trim";
  import PromptTemplate from "./PromptTemplate.svelte";
  import {
    primitiveTaskState,
    primitiveTaskExecutionStates,
  } from "../ExecutionStates.svelte";
  import ExecutionResultInspection from "./ExecutionResultInspection.svelte";
  import PromptToolInspection from "./PromptToolInspection.svelte";
  import CodeToolInspection from "./CodeToolInspection.svelte";
  let {
    task,
  }: {
    task: tPrimitiveTask | undefined;
  } = $props();
  let show_description = $state(true);
  let show_formats = $state(false);
  let show_execution = $state(false);
  let execution_states = $derived(
    primitiveTaskExecutionStates.execution_states
  );
  let executed = $derived.by(() => {
    if (task === undefined) return false;
    return execution_states?.[task.id]?.executed;
  });
  $inspect(executed);
  let execution_result_inspection_panel: any = $state();

  function handleUpdatePrompt(messages) {
    const new_task = JSON.parse(JSON.stringify(task));
    new_task.execution!.parameters.prompt_template = messages;
    console.log("Updated primitive task", new_task);
    if (task !== undefined)
      primitiveTaskState.updatePrimitiveTask(task.id, new_task);
  }

  export async function navigate_to_results() {
    await tick();
    execution_result_inspection_panel.navigate_to_results();
  }

  onMount(() => {
    console.log({ task });
  });
</script>

<div class="flex flex-col px-1 gap-y-2">
  <div
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-[#f2f8fd] flex justify-center"
  >
    {task?.label} - Detail
  </div>
  {#if task}
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
          <button
            class="header-2"
            tabindex="0"
            onclick={async () => {
              show_formats = !show_formats;
              await tick();
              document
                .querySelector(".format-container")
                ?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
          >
            Input/Output Formats
            {#if task.recompile_needed_IO}
              <div
                class="flex items-center gap-x-1 text-slate-700 italic text-sm ml-2"
                title="Recompile Needed"
              >
                <svg
                  class="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#45556c"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  ><circle cx="12" cy="12" r="10" /><path
                    d="m14.31 8 5.74 9.94"
                  /><path d="M9.69 8h11.48" /><path
                    d="m7.38 12 5.74-9.94"
                  /><path d="M9.69 16 3.95 6.06" /><path
                    d="M14.31 16H2.83"
                  /><path d="m16.62 12-5.74 9.94" /></svg
                >
              </div>
            {/if}
            <img
              src="chevron_down.svg"
              alt="expand"
              class="hidden ml-auto w-5 h-5"
            />
          </button>
          {#if task.doc_input_keys}
            {#if show_formats}
              {@const input_key_options =
                task.existing_keys?.filter(
                  (k) => !task.doc_input_keys?.includes(k)
                ) || []}
              <div
                in:slide
                class="format-container flex justify-around divide-x"
              >
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
                    <div class="option-value relative">
                      {doc_input_key}
                      <button
                        class="option-value-delete-icon hidden justify-center items-center absolute top-0 bottom-0 left-0 right-0 bg-gray-200"
                        onclick={() => {
                          const new_task = JSON.parse(JSON.stringify(task));
                          new_task.doc_input_keys = task.doc_input_keys!.filter(
                            (key) => key !== doc_input_key
                          );
                          if (new_task.execution.tool === "prompt_tool") {
                            new_task.execution.parameters.prompt_template[1].content = `${new_task.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
                          } else {
                            new_task.recompile_needed_IO = false;
                            new_task.recompile_needed_parameters = true;
                          }
                          primitiveTaskState.updatePrimitiveTask(
                            task.id,
                            new_task,
                            true
                          );
                        }}
                        ><img
                          src="minus.svg"
                          class="w-4 h-4"
                          alt="delete"
                        /></button
                      >
                    </div>
                  {/each}

                  <div class="relative flex flex-wrap gap-1 px-1">
                    {#if input_key_options.length === 0}
                      <div
                        class="w-max px-1 text-gray-600 text-sm italic select-none"
                      >
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
                            onclick={(e: any) => {
                              const new_task = JSON.parse(JSON.stringify(task));
                              new_task.doc_input_keys = [
                                ...task.doc_input_keys!,
                                existing_key,
                              ];
                              if (new_task.execution.tool === "prompt_tool") {
                                new_task.execution.parameters.prompt_template[1].content = `${new_task.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
                              } else {
                                new_task.recompile_needed_IO = false;
                                new_task.recompile_needed_parameters = true;
                              }
                              primitiveTaskState.updatePrimitiveTask(
                                task.id,
                                new_task,
                                true
                              );
                            }}
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
                        primitiveTaskState.updateOutputKey(
                          task.id,
                          state_output_key
                        );
                      }}
                      onkeydown={(e: any) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          e.target.blur();
                        }
                      }}
                    >
                      {task.state_output_key}
                    </div>
                    <!-- <div
                      class="delete hidden absolute right-0 top-1 bottom-1 items-center cursor-pointer hover:bg-red-200 p-1 rounded-full"
                    >
                      <img src="trash.svg" alt="delete" class="w-5 h-5" />
                    </div> -->
                  </div>
                </div>
              </div>
            {/if}
          {:else}
            <div
              class="flex items-center gap-x-1 text-slate-700 italic text-sm"
            >
              <svg
                class="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#405065"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                ><circle cx="12" cy="12" r="10" /><path
                  d="m14.31 8 5.74 9.94"
                /><path d="M9.69 8h11.48" /><path d="m7.38 12 5.74-9.94" /><path
                  d="M9.69 16 3.95 6.06"
                /><path d="M14.31 16H2.83" /><path
                  d="m16.62 12-5.74 9.94"
                /></svg
              >
              Needs Compilation...
            </div>
          {/if}
        </div>
        <button
          tabindex="0"
          class="header-2"
          onclick={async () => {
            show_execution = !show_execution;
            await tick();
            document
              .querySelector(".execution-container")
              ?.scrollIntoView({ behavior: "smooth", block: "center" });
          }}
        >
          Execution Parameter
          {#if task.recompile_needed_parameters}
            <div
              class="flex items-center gap-x-1 text-slate-700 italic text-sm ml-2"
              title="Recompile Needed"
            >
              <svg
                class="w-5 h-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#45556c"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                ><circle cx="12" cy="12" r="10" /><path
                  d="m14.31 8 5.74 9.94"
                /><path d="M9.69 8h11.48" /><path d="m7.38 12 5.74-9.94" /><path
                  d="M9.69 16 3.95 6.06"
                /><path d="M14.31 16H2.83" /><path
                  d="m16.62 12-5.74 9.94"
                /></svg
              >
            </div>
          {/if}
          <img
            src="chevron_down.svg"
            alt="expand"
            class="hidden ml-auto w-5 h-5"
          />
        </button>
        {#if task.execution}
          {#if show_execution}
            <div
              in:slide
              class="execution-container flex flex-col divide-y divide-gray-400 divide-dashed pb-2 px-1"
            >
              {#if task.execution.tool === "prompt_tool"}
                <PromptToolInspection {task} {handleUpdatePrompt} />
              {:else}
                <CodeToolInspection {task} />
              {/if}
            </div>
          {/if}
        {:else}
          <div class="flex items-center gap-x-1 text-slate-700 italic text-sm">
            <svg
              class="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#405065"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              ><circle cx="12" cy="12" r="10" /><path
                d="m14.31 8 5.74 9.94"
              /><path d="M9.69 8h11.48" /><path d="m7.38 12 5.74-9.94" /><path
                d="M9.69 16 3.95 6.06"
              /><path d="M14.31 16H2.83" /><path d="m16.62 12-5.74 9.94" /></svg
            >
            Needs Compilation...
          </div>
        {/if}
      </div>
      {#if executed}
        <ExecutionResultInspection
          bind:this={execution_result_inspection_panel}
          task_id={task.id}
        />
      {:else}
        <div class="flex flex-col gap-y-1">
          <div class="header-2 pointer-events-none opacity-70">Result</div>
          <span class="text-xs text-gray-500 itliac px-1">
            (Not Executed)
          </span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 bg-blue-100 px-1 cursor-pointer hover:bg-blue-200 flex items-center;
  }
  .header-2:hover > img {
    @apply block;
  }
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
