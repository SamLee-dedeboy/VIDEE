<script lang="ts">
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
  } from "types";
  import DocumentCard from "./DocumentCard.svelte";
  import { slide } from "svelte/transition";
  import { onMount, tick } from "svelte";
  import { server_address } from "constants";
  import { getContext } from "svelte";
  import PromptTemplate from "./PromptTemplate.svelte";
  import { primitiveTaskState } from "../ExecutionStates.svelte";
  import PagedDocuments from "./PagedDocuments.svelte";
  let {
    task,
    // handleUpdatePrimitiveTask,
  }: {
    task: tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution>;
    // handleUpdatePrimitiveTask: Function;
  } = $props();
  let show_description = $state(true);
  let show_formats = $state(false);
  let show_execution = $state(false);
  let show_result = $state(false);
  let result = $state(undefined);
  const session_id = (getContext("session_id") as Function)();

  function handleFetchTaskResult() {
    fetch(`${server_address}/primitive_task/result/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ task_id: task.id, session_id }),
    })
      .then((response) => response.json())
      .then(async (data) => {
        console.log("Inspection fetched result:", data);
        result = data.result;
        await tick();
        document.querySelector(".result-panel")?.scrollIntoView({
          behavior: "smooth",
        });
        // await tick();
        // const inspection_panel = document.querySelector(".inspection-panel");
        // if (inspection_panel && show_result) {
        //   inspection_panel.scrollTop = inspection_panel.scrollHeight;
        // }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
  function handleUpdatePrompt(messages) {
    task.execution!.parameters.prompt_template = messages;
    console.log("Updated primitive task", $state.snapshot(task));
    primitiveTaskState.updatePrimitiveTask(task.id, task);
  }
  onMount(() => {
    console.log({ task });
  });
</script>

<div class="flex flex-col px-1 gap-y-2">
  <div
    class="text-[1.5rem] text-slate-600 font-semibold italic bg-[#f2f8fd] flex justify-center"
  >
    {task.label} - Detail
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
          <button
            class="header-2"
            tabindex="0"
            onclick={async () => {
              show_formats = !show_formats;
              await tick();
              document
                .querySelector(".format-container")
                ?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            Input/Output Formats
            <img
              src="chevron_down.svg"
              alt="expand"
              class="hidden ml-auto w-5 h-5"
            />
          </button>
          {#if task.doc_input_keys}
            {#if show_formats}
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
        <button
          tabindex="0"
          class="header-2"
          onclick={async () => {
            show_execution = !show_execution;
            await tick();
            document
              .querySelector(".execution-container")
              ?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          Execution
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
                    <PromptTemplate
                      messages={value}
                      {handleUpdatePrompt}
                      --bg-color="oklch(0.97 0.014 254.604)"
                      --border-color="#bedbff"
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
        {:else}
          <div>Needs Compilation...</div>
        {/if}
      </div>
      {#if true}
        <div class="flex flex-col">
          <div class="flex flex-col">
            <button
              tabindex="0"
              class="header-2"
              onclick={async () => {
                show_result = !show_result;
                handleFetchTaskResult();
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
            <div in:slide class="result-panel flex flex-col">
              {#each Object.keys(result) as state_input_key}
                <div class="flex flex-col state-container">
                  <button
                    class="state-key border-b-2 border-gray-200 italic text-slate-600 hover:bg-gray-200"
                    onclick={(e: any) => {
                      console.log(e.target);
                      const container = e.target.closest(".state-container");
                      const state_content =
                        container.querySelector(".state-content");
                      state_content.classList.toggle("hide-state-content");
                      state_content.scrollIntoView({ behavior: "smooth" });
                    }}>{state_input_key}</button
                  >
                  <div class="state-content flex hide-state-content flex-col">
                    <PagedDocuments
                      documents={result[state_input_key]}
                      bg_color="oklch(0.97 0.014 254.604)"
                      bg_hover_color="oklch(0.882 0.059 254.128)"
                    ></PagedDocuments>
                  </div>
                  <!-- <div class="flex flex-wrap gap-2">
                    {#each result[state_input_key] as doc}
                      <DocumentCard
                        document={doc}
                        --bg-color="oklch(0.97 0.014 254.604)"
                        --bg-hover-color="oklch(0.882 0.059 254.128)"
                      />
                    {/each}
                  </div> -->
                </div>
              {/each}
            </div>
            <div class="h-[10rem]"></div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
  <!-- <ExecutionEvaluators --bg-color={"#f2f8fd"} tasks={primitive_tasks}
  ></ExecutionEvaluators> -->
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
  .hide-state-content {
    @apply hidden;
  }
</style>
