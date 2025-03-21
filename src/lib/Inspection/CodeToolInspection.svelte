<script lang="ts">
  let { task } = $props();
  const parameter_keys = {
    data_transform_tool: ["name", "transform_code"],
    embedding_tool: ["name", "provider", "model"],
    clustering_tool: ["name", "algorithm", "feature_key", "n_clusters"], // there are more, but these are the most important
  };
</script>

<div class="flex gap-x-2 items-center py-1">
  <div class="text-gray-700">Execution Method -</div>
  <div class="option-value">{task.execution.tool}</div>
</div>
<div class="flex flex-col gap-y-2">
  <div class="text-gray-700">Parameters</div>
  {#each parameter_keys[task.execution.tool] as key}
    <div class="flex items-center gap-x-2 flex-wrap">
      <div class="italic text-gray-600">{key}</div>
      <div class="option-value">
        {task.execution.parameters[key]}
      </div>
    </div>
  {/each}
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .option-value {
    @apply outline-1 outline-gray-300 rounded px-2 hover:bg-gray-200 transition-all cursor-pointer flex justify-center font-mono text-xs;
  }
</style>
