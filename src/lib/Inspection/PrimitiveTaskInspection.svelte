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
  import IOInspection from "./IOInspection.svelte";
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
      primitiveTaskState.updatePrimitiveTask(task.id, new_task, true);
  }

  export async function navigate_to_results() {
    await tick();
    execution_result_inspection_panel.navigate_to_results();
  }

  onMount(() => {
    console.log({ task });
  });
  
  function handleDeleteDocInputKey(doc_input_key) {
    if (!task) return;
    // Deleting the clicked input key..
    const new_task = JSON.parse(JSON.stringify(task));
    new_task.doc_input_keys = task.doc_input_keys!.filter(
      (key) => key !== doc_input_key
    );
    new_task.input_keys = new_task.input_keys?.filter(
      (obj) => obj.key !== doc_input_key
    );
    if (new_task.execution?.parameters?.feature_key && new_task.execution.parameters.feature_key === doc_input_key) {
      new_task.execution.parameters.feature_key = null;
    }                         
    // Update schema if using code tool
    if (new_task.execution?.parameters?.input_key_schemas) {
      const schemas = {...new_task.execution.parameters.input_key_schemas};
      delete schemas[doc_input_key];
      new_task.execution.parameters.input_key_schemas = schemas;
    }
    
    if (new_task.execution.tool === "prompt_tool") {
      new_task.execution.parameters.prompt_template[1].content = `${new_task.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
      new_task.recompile_skip_IO = true;
    } else {
      new_task.recompile_skip_IO = true;
      new_task.recompile_skip_parameters = false;
    }
    primitiveTaskState.updatePrimitiveTask(
      task.id,
      new_task,
      true
    );
  }
  
  function handleAddDocInputKey(existing_key) {
    if (!task) return;
    // Add the new key to doc_input_keys..
    const new_task = JSON.parse(JSON.stringify(task));
    new_task.doc_input_keys = [
      ...task.doc_input_keys!,
      existing_key,
    ];
    
    // Find the schema for this key from available_states
    let keySchema = null;
    if (new_task.state_input_key && new_task.available_states && 
        new_task.available_states[new_task.state_input_key]) {
      const keyInfo = new_task.available_states[new_task.state_input_key]
        .find(k => k.key === existing_key);
      if (keyInfo) {
        keySchema = keyInfo.schema;
      }
    }

    new_task.input_keys = [...(new_task.input_keys || []), {key: existing_key, schema: keySchema}];
    
    // Update schema in execution parameters
    if (new_task.execution?.parameters) {
      if (!new_task.execution.parameters.input_key_schemas) {
        new_task.execution.parameters.input_key_schemas = {};
      }
      new_task.execution.parameters.input_key_schemas[existing_key] = keySchema;
    }
    // Update feature key if using code tool
    if (new_task.execution?.parameters?.feature_key) {
      new_task.execution.parameters.feature_key = existing_key;
    }
    
    if (new_task.execution.tool === "prompt_tool") {
      new_task.execution.parameters.prompt_template[1].content = `${new_task.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
      new_task.recompile_skip_IO = true;
    } else {
      new_task.recompile_skip_IO = true;
      new_task.recompile_skip_parameters = false;
    }
    primitiveTaskState.updatePrimitiveTask(
      task.id,
      new_task,
      true
    );
  }
  
  function handleDeleteStateInputKey() {
    if (!task) return;
    const new_task = JSON.parse(JSON.stringify(task));
    const old_state_input_key = new_task.state_input_key;
    new_task.state_input_key = "";
    
    // Clear doc_input_keys related to the old state
    if (old_state_input_key && new_task.available_states && new_task.available_states[old_state_input_key]) {
      const old_state_keys = new_task.available_states[old_state_input_key].map(k => k.key);
      if (new_task.doc_input_keys) {
        new_task.doc_input_keys = new_task.doc_input_keys.filter(k => !old_state_keys.includes(k));
      }
    }
    
    if (new_task.execution?.tool === "prompt_tool") {
      new_task.recompile_skip_IO = true;
    } else {
      new_task.recompile_skip_IO = true;
    }
    primitiveTaskState.updatePrimitiveTask(
      task.id,
      new_task,
      true
    );
  }
  
  function handleAddStateInputKey(state_key) {
    if (!task) return;
    const new_task = JSON.parse(JSON.stringify(task));
    const old_state_input_key = new_task.state_input_key;
    new_task.state_input_key = state_key;
    
    // Update doc_input_keys based on the available keys in the selected state
    if (new_task.available_states && new_task.available_states[state_key]) {
      // Get available keys for the selected state
      const available_keys = new_task.available_states[state_key].map(k => k.key);
      
      // Reset doc_input_keys
      if (!new_task.doc_input_keys) {
        new_task.doc_input_keys = [];
      } else {
        // Filter out keys that were from the old state
        if (old_state_input_key && new_task.available_states[old_state_input_key]) {
          const old_state_keys = new_task.available_states[old_state_input_key].map(k => k.key);
          new_task.doc_input_keys = new_task.doc_input_keys.filter(k => !old_state_keys.includes(k));
          new_task.existing_keys = new_task.existing_keys?.filter(k => !old_state_keys.includes(k));
          new_task.input_keys = new_task.input_keys?.filter(obj => !old_state_keys.includes(obj.key));
        }
      }
      
      // Add the first available key from the new state
      if (available_keys.length > 0 && !new_task.doc_input_keys.includes(available_keys[0])) {
        new_task.doc_input_keys.push(available_keys[0]);
        new_task.existing_keys = [...(new_task.existing_keys || []), available_keys[0]];
        new_task.input_keys = [...(new_task.input_keys || []), {
          key: available_keys[0], 
          schema: new_task.available_states[state_key].find(k => k.key === available_keys[0])?.schema
        }];
        
        if (!new_task.execution.parameters.input_key_schemas) {
          new_task.execution.parameters.input_key_schemas = {};
        }
        
        new_task.execution.parameters.input_key_schemas = new_task.input_keys?.reduce((acc, obj) => {
          acc[obj.key] = obj.schema;
          return acc;
        }, {});
      }
    }
    
    if (new_task.execution?.tool === "prompt_tool") {
      // Update prompt template content with new doc_input_keys from the new state
      new_task.execution.parameters.prompt_template[1].content = `${new_task.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
      new_task.recompile_skip_IO = true;
    } else {
      new_task.recompile_skip_IO = true;
      new_task.recompile_skip_parameters = false;
    }
    
    primitiveTaskState.updatePrimitiveTask(
      task.id,
      new_task,
      true
    );
  }
</script>

{#key task?.id}
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
              {#if task.recompile_skip_IO}
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
                  task.state_input_key &&
                  task.available_states &&
                  task.available_states[task.state_input_key]
                    ? task.available_states[task.state_input_key]
                        .map((k) => k.key)
                        .filter((k) => !task.doc_input_keys?.includes(k))
                    : []}
                <IOInspection
                  {input_key_options}
                  state_input_key={task.state_input_key || ""}
                  doc_input_keys={task.doc_input_keys}
                  state_output_key={task.state_output_key}
                  available_states={task.available_states}
                  {handleDeleteDocInputKey}
                  {handleAddDocInputKey}
                  {handleDeleteStateInputKey}
                  {handleAddStateInputKey}
                  handleEditStateOutputKey={(state_output_key) => {
                    primitiveTaskState.updateOutputKey(
                      task.id,
                      state_output_key
                    );
                  }}
                />
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
                  /><path d="M9.69 8h11.48" /><path
                    d="m7.38 12 5.74-9.94"
                  /><path d="M9.69 16 3.95 6.06" /><path
                    d="M14.31 16H2.83"
                  /><path d="m16.62 12-5.74 9.94" /></svg
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
            {#if task.recompile_skip_parameters}
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
{/key}

<style lang="postcss">
  @reference "tailwindcss";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 bg-blue-100 px-1 cursor-pointer hover:bg-blue-200 flex items-center;
  }
  .header-2:hover > img {
    @apply block;
  }
</style>