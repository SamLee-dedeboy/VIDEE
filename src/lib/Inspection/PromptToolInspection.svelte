<script lang="ts">
  import PromptTemplate from "./PromptTemplate.svelte";
  let { task, handleUpdatePrompt } = $props();
</script>

<div class="flex gap-x-2 items-center py-1">
  <div class="text-gray-700">Execution Method -</div>
  <div class="option-value">{task.execution.tool}</div>
</div>
<div class="flex flex-col gap-y-2">
  <div class="text-gray-700">Parameters</div>
  {#each ["model", "format", "name"] as key}
    <div class="flex items-center gap-x-2">
      <div class="italic text-gray-600 w-[3rem]">{key}</div>
      <div class="option-value">
        {task.execution.parameters[key]}
      </div>
    </div>
  {/each}
  <PromptTemplate
    messages={task.execution.parameters.prompt_template}
    {handleUpdatePrompt}
    --bg-color="oklch(0.97 0.014 254.604)"
    --border-color="#bedbff"
  ></PromptTemplate>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .option-value {
    @apply outline-1 outline-gray-300 rounded px-2 hover:bg-gray-200 transition-all cursor-pointer flex justify-center font-mono text-xs;
  }
</style>
