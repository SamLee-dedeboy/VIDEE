<script lang="ts">
  let { messages } = $props();
</script>

<div class="container flex flex-col border-x-2 border-t-2 border-dashed">
  <div
    class="title flex text-slate-700 justify-center font-mono text-lg border-b border-gray-300"
  >
    Prompt Template
  </div>
  <div class="flex divide-x divide-dashed">
    {#each messages as prompt_template_message}
      {#if prompt_template_message.role === "system"}
        <div class="flex flex-[2_2_0%] flex-col gap-x-2">
          <div class="flex justify-center bg-gray-100 font-mono">
            System Instruction
          </div>
          <div
            class="bg-white text-slate-600 px-1 whitespace-pre-line max-h-[20rem] overflow-y-auto"
          >
            {prompt_template_message.content.trim()}
          </div>
        </div>
      {:else if prompt_template_message.role === "human"}
        <div class="flex flex-1 flex-col gap-x-2">
          <div class="flex justify-center bg-gray-100 font-mono">
            Input Data
          </div>
          <div class="bg-white text-slate-600 grow px-1 whitespace-pre-line">
            {prompt_template_message.content.trim()}
          </div>
        </div>
      {/if}
    {/each}
  </div>
</div>

<style lang="postcss">
  .title {
    background-color: var(--bg-color);
  }
  .container {
    border-color: var(--border-color);
  }
</style>
