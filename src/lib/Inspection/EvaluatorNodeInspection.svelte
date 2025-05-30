<script lang="ts">
  import { slide } from "svelte/transition";
  import { setContext, tick } from "svelte";
  import PromptTemplate from "./PromptTemplate.svelte";
  import type {
    tExecutionEvaluator,
    tExecutionEvaluatorResult,
    tDocument,
  } from "types";
  import { server_address } from "constants";
  import { getContext } from "svelte";
  import { evaluatorState, session_id } from "../ExecutionStates.svelte";
  import EvaluatorResult from "../Evaluation/EvaluatorResult.svelte";
  import EvaluatorResultRadialChart from "../Evaluation/EvaluatorResultRadialChart.svelte";
  import PagedDocuments from "./PagedDocuments.svelte";
  import IoInspection from "./IOInspection.svelte";
  import SimplifiedListView from "./SimplifiedListView.svelte";

  let {
    evaluator = $bindable(),
  }: {
    evaluator: tExecutionEvaluator;
  } = $props();
  let show_description = $state(true);
  let show_formats = $state(false);
  let show_execution = $state(false);
  let show_result = $state(false);
  let show_documents = $state(true);
  let paged_document_component: any = $state();
  let viz_mode = $state("bar"); // "bar" or "radial"

  let result: tExecutionEvaluatorResult | undefined = $state(undefined);
  $effect(() => {
    handleFetchEvaluationResult(evaluator);
  });
  function handleFetchEvaluationResult(evaluator: tExecutionEvaluator) {
    console.log({ evaluator });
    fetch(`${server_address}/primitive_task/evaluators/result/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id,
        evaluator_name: evaluator.name,
        task_id: evaluator.task,
      }),
    })
      .then((response) => response.json())
      .then(async (data) => {
        console.log("Evaluation result:", data);
        result = data.result;
        await tick();
        const inspection_panel = document.querySelector(".inspection-panel");
        if (inspection_panel)
          inspection_panel.scroll({
            top: inspection_panel.scrollHeight,
            behavior: "smooth",
          });
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function handleUpdatePrompt(messages) {
    evaluator.parameters!.prompt_template = messages;
    console.log("Updated evaluator", $state.snapshot(evaluator));
    evaluatorState.updateEvaluator(evaluator.name, evaluator);
  }

  async function handleDocumentClicked(doc: tDocument) {
    show_documents = true;
    await tick();
    paged_document_component.navigateToDoc(doc);
  }
  setContext("navigate_to_doc", handleDocumentClicked);

  export async function navigate_to_results() {
    await tick();
    show_result = true;
    handleFetchEvaluationResult(evaluator);
  }
</script>

{#key evaluator.name}
  <div class="flex flex-col px-1 gap-y-2">
    <div
      class="text-[1.5rem] text-slate-600 font-semibold italic bg-emerald-100 flex justify-center items-center"
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
              {@const input_key_options =
                evaluator.existing_keys?.filter(
                  (k) => !evaluator.doc_input_keys?.includes(k)
                ) || []}
              <IoInspection
                {input_key_options}
                state_input_key={evaluator.state_input_key!}
                doc_input_keys={evaluator.doc_input_keys}
                state_output_key={evaluator.state_output_key!}
                handleDeleteDocInputKey={(doc_input_key) => {
                  console.log("Deleting", doc_input_key);
                  const new_evaluator = JSON.parse(JSON.stringify(evaluator));
                  new_evaluator.doc_input_keys =
                    evaluator.doc_input_keys?.filter(
                      (k) => k !== doc_input_key
                    );
                  new_evaluator.parameters.prompt_template[1].content = `${new_evaluator.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
                  evaluatorState.updateEvaluator(evaluator.name, new_evaluator);
                }}
                handleAddDocInputKey={(doc_input_key) => {
                  const new_evaluator = JSON.parse(JSON.stringify(evaluator));
                  new_evaluator.doc_input_keys = [
                    ...(evaluator.doc_input_keys || []),
                    doc_input_key,
                  ];
                  new_evaluator.parameters.prompt_template[1].content = `${new_evaluator.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
                  evaluatorState.updateEvaluator(evaluator.name, new_evaluator);
                }}
                handleEditStateOutputKey={(state_output_key) => {
                  const new_evaluator = JSON.parse(JSON.stringify(evaluator));
                  new_evaluator.state_output_key = state_output_key;
                  evaluatorState.updateEvaluator(evaluator.name, new_evaluator);
                }}
              ></IoInspection>
              <!-- <div in:slide class="flex justify-around divide-x divide-dashed">
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
            </div> -->
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
                <div class="flex items-center gap-x-2">
                  <div class="italic text-gray-600 w-[3rem]">name</div>
                  <div class="option-value">{evaluator.parameters.name}</div>
                </div>
                <div class="flex gap-x-4">
                  <div class="flex items-center gap-x-2">
                    <div class="italic text-gray-600 w-[3rem]">model</div>
                    <div class="option-value">{evaluator.parameters.model}</div>
                  </div>
                  <div class="flex items-center gap-x-2">
                    <div class="italic text-gray-600 w-[3rem]">format</div>
                    <div class="option-value">
                      {evaluator.parameters.format}
                    </div>
                  </div>
                </div>
                <PromptTemplate
                  messages={evaluator.parameters.prompt_template}
                  {handleUpdatePrompt}
                  --bg-color="#f6fffb"
                  --border-color="#00d492"
                ></PromptTemplate>
              </div>
            </div>
          {/if}
        {/if}
      </div>
      {#if result}
        <div class="flex flex-col">
          <div class="flex flex-col">
            <button
              tabindex="0"
              class="header-2"
              onclick={async () => {
                show_result = !show_result;
                handleFetchEvaluationResult(evaluator);
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
          {#if show_result}
            <div class="evaluation-result-panel flex flex-col gap-y-2">
              {#if evaluator.state_input_key === "documents"}
                <button
                  class="state-key border-b-2 border-gray-200 italic text-slate-600 hover:bg-gray-200 shadow-xs"
                  onclick={() => {
                    show_documents = !show_documents;
                  }}
                  onkeyup={() => {}}
                >
                  documents
                </button>
                {#if show_documents}
                  <div class="shadow-xs">
                    <PagedDocuments
                      bind:this={paged_document_component}
                      documents={result.result.documents}
                      bg_color="#f6fffb"
                      bg_hover_color="oklch(0.905 0.093 164.15)"
                    ></PagedDocuments>
                  </div>
                {/if}
              {:else}
                {@const state_value =
                  result.result["global_store"][evaluator.state_input_key]}
                <button
                  class="state-key border-b-2 border-gray-200 italic text-slate-600 hover:bg-gray-200 shadow-xs"
                  onclick={async (e: any) => {
                    console.log(e.target);
                    show_documents = !show_documents;
                  }}>{evaluator.state_input_key}</button
                >
                <SimplifiedListView
                  items={state_value}
                  bg_color="oklch(0.97 0.014 254.604)"
                  bg_hover_color="oklch(0.882 0.059 254.128)"
                />
              {/if}
              <div
                class="flex border-b-2 border-gray-200 italic text-slate-600 divide-x divide-gray-200 shadow-xs"
              >
                <button
                  class="flex-1 hover:bg-gray-200 text-center"
                  onclick={() => (viz_mode = "bar")}>Frequency</button
                >
                {#if evaluator.state_input_key === "documents"}
                  <button
                    class="flex-1 hover:bg-gray-200 text-center"
                    onclick={() => (viz_mode = "radial")}>Distribution</button
                  >
                {/if}
              </div>
              {#if viz_mode === "bar"}
                <EvaluatorResult
                  {result}
                  state_input_key={evaluator.state_input_key!}
                ></EvaluatorResult>
              {:else if viz_mode === "radial"}
                <EvaluatorResultRadialChart {result}
                ></EvaluatorResultRadialChart>
              {/if}
            </div>
          {/if}
        </div>
      {:else}
        <div class="flex flex-col gap-y-1">
          <div class="header-2 pointer-events-none opacity-70">Result</div>
          <span class="text-xs text-gray-500 itliac px-1">
            (Not Executed)
          </span>
        </div>
      {/if}
    </div>
  </div>
{/key}

<style lang="postcss">
  @reference "tailwindcss";
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
</style>
