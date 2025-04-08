<script lang="ts">
  import { trim } from "lib/trim";
  import { primitiveTaskState } from "../ExecutionStates.svelte";
  import DatasetInspection from "./DatasetInspection.svelte";
  import { tool_options } from "./tool_options";
  import CodeToolOption from "./CodeToolOption.svelte";
  import type {
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
  } from "types";
  let { task }: { task: tPrimitiveTaskDescription & tPrimitiveTaskExecution } =
    $props();
  $inspect(task);
  const method_keys = {
    data_transform_tool: "name",
    embedding_tool: "provider",
    clustering_tool: "algorithm",
  };
  let tool_method = $derived(
    tool_options[task.execution.tool].find(
      (method) =>
        method[method_keys[task.execution.tool]] ===
        task.execution.parameters[method_keys[task.execution.tool]]
    )
  );
  let tool_method_options = $derived(
    tool_options[task.execution.tool].map(
      (method) => method[method_keys[task.execution.tool]]
    )
  );

  function updateTaskParameter(key, value) {
    const new_task = JSON.parse(JSON.stringify(task));
    new_task.execution.parameters[key] = value;
    new_task.recompile_skip_parameters = false;
    primitiveTaskState.updatePrimitiveTask(task.id, new_task, true);
  }
</script>

<div class="flex gap-x-2 items-center py-1">
  <div class="text-gray-700">Execution Method -</div>
  <div class="param-value">{task.execution.tool}</div>
</div>
<div class="flex flex-col gap-y-2">
  <div class="text-gray-700">Parameters</div>
  <!-- <div class="flex gap-x-2 items-center">
    <div class="text-gray-700">Name</div>
    <div class="font-mono italic text-sm">{task.execution.parameters.name}</div>
  </div> -->
  <div class="flex items-center gap-x-2 shadow py-1 px-2">
    <div class="param-label">{method_keys[task.execution.tool]}</div>
    <div class="param-value option-trigger relative z-10">
      {task.execution.parameters[method_keys[task.execution.tool]]}
      <div class="option-value-container">
        {#each tool_method_options as option}
          <button
            class="option-value"
            onclick={() =>
              updateTaskParameter(method_keys[task.execution.tool], option)}
          >
            {option}
          </button>
        {/each}
      </div>
    </div>
  </div>
  <div class="flex gap-x-2 shadow py-1 px-2">
    <div class="param-label shrink-0">Good For</div>
    <div class="param-value">{tool_method["Good for"]}</div>
  </div>
  <!-- parameters -->
  {#each Object.keys(tool_method.parameters) as key}
    <div class="flex gap-x-2 items-center shadow py-1 px-2">
      <div class="param-label" title={tool_method.parameters[key].description}>
        {key}
      </div>
      <CodeToolOption
        value={task.execution.parameters[key] || "*Input a value"}
        type_info={tool_method.parameters[key]}
        handleUpdate={(new_value) => updateTaskParameter(key, new_value)}
      ></CodeToolOption>
    </div>
  {/each}
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .param-label {
    @apply text-gray-700 text-sm;
  }
  .param-value {
    @apply font-mono italic text-sm text-slate-800;
  }
  .option-trigger {
    @apply cursor-pointer hover:bg-gray-200 rounded outline-1 outline-gray-300 px-2;
  }
  .option-trigger:hover .option-value-container {
    @apply flex;
  }
  .option-value-container {
    @apply w-max absolute top-full left-1/2 -translate-x-1/2 hidden flex-col outline-1 outline-gray-300 bg-white divide-y divide-gray-200;
  }
  .option-value {
    @apply cursor-pointer hover:bg-gray-200 px-2;
  }
  /* .option-value {
    @apply outline-1 outline-gray-300 rounded px-2 hover:bg-gray-200 transition-all cursor-pointer flex justify-center font-mono text-xs;
  } */
</style>
