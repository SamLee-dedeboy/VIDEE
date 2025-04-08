<script lang="ts">
  import { trim } from "lib/trim";
  let { messages, handleUpdatePrompt } = $props();
  function highlight_variables(text: string) {
    return text;
    console.log("highlight_variables", text);
    // replace ${var} with <span class="bg-yellow-200">${var}</span>
    return text.replace(
      /\{(.*?)}/g,
      '<span class="text-yellow-600 italic text-sm" contenteditable=true>{$1}</span>'
    );
  }
</script>

<div class="container flex flex-col border-x-2 border-t-2 border-dashed">
  <div
    class="title flex text-slate-700 justify-center font-mono text-lg border-b border-gray-300"
  >
    Prompt Template
  </div>
  <div class="flex divide-x divide-dashed">
    {#each messages as prompt_template_message, index}
      {#if prompt_template_message.role === "system"}
        <div class="flex flex-[2_2_0%] flex-col gap-x-2">
          <div class="flex justify-center bg-gray-100 font-mono">
            System Instruction
          </div>
          <div
            use:trim
            class="bg-white text-slate-600 px-1 whitespace-pre-line max-h-[20rem] overflow-y-auto"
            contenteditable="true"
            onblur={(event: any) => {
              let messages_copy = JSON.parse(JSON.stringify(messages));
              messages_copy[index].content = event.target.innerText;
              handleUpdatePrompt(messages_copy);
              event.target.innerHTML = messages_copy[index].content;
            }}
          >
            {prompt_template_message.content.trim()}
          </div>
        </div>
      {:else if prompt_template_message.role === "human"}
        <div class="flex flex-1 flex-col gap-x-2 relative">
          <div class="flex justify-center bg-gray-100 font-mono">
            Input Data
          </div>
          <div
            use:trim
            contenteditable
            class="bg-white text-slate-600 grow px-1 whitespace-pre-line"
            onblur={(event: any) => {
              console.log(event.target);
              let messages_copy = JSON.parse(JSON.stringify(messages));
              messages_copy[index].content = event.target.innerText;
              handleUpdatePrompt(messages_copy);
              event.target.innerHTML = highlight_variables(
                messages_copy[index].content.trim()
              );
            }}
          >
            {@html highlight_variables(prompt_template_message.content.trim())}
          </div>
          <div class="absolute right-1 bottom-0">
            <span class="text-yellow-600 italic text-xs"
              >&#123x&#125 - template variable</span
            >
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
