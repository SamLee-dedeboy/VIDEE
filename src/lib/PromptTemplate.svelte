<script lang="ts">
  let { messages } = $props();
</script>

<div
  class="flex flex-col border-x-2 border-t-2 border-dashed border-blue-300 shadow"
>
  <div
    class="flex text-slate-500 justify-center font-mono text-lg bg-blue-50 border-b border-gray-300"
  >
    Prompt Template
  </div>
  <div class="flex">
    {#each messages as prompt_template_message}
      {#if prompt_template_message.role === "system"}
        <div class="flex flex-[2_2_0%] flex-col gap-x-2 divide-x">
          <div class="flex justify-center bg-blue-100 font-mono">
            System Instruction
          </div>
          <div
            class="bg-blue-50 px-1 whitespace-pre-line max-h-[20rem] overflow-y-auto"
          >
            {prompt_template_message.content.trim()}
          </div>
        </div>
      {:else if prompt_template_message.role === "human"}
        <div class="flex flex-1 flex-col gap-x-2 divide-x">
          <div class="flex justify-center bg-orange-100 font-mono">
            Input Data
          </div>
          <div class="bg-orange-50 grow px-1 whitespace-pre-line">
            {prompt_template_message.content.trim()}
          </div>
        </div>
      {/if}
    {/each}
  </div>
</div>
