<script lang="ts">
  let { value, type_info, handleUpdate } = $props();
</script>

{#if ["int", "float"].includes(type_info.type)}
  <div
    class="param-value px-2"
    contenteditable
    onblur={(e: any) => {
      const new_value = parseFloat(e.target.innerText);
      if (new_value !== value) {
        handleUpdate(new_value);
      }
    }}
  >
    {value}
  </div>
{:else if ["bool", "boolean"].includes(type_info.type)}
  <div class="param-value option-trigger relative">
    {value ? "True" : "False"}
    <div class="option-value-container">
      {#each ["True", "False"] as option}
        <button class="option-value" onclick={() => handleUpdate(option)}
          >{option}</button
        >
      {/each}
    </div>
  </div>
{:else if ["enum"].includes(type_info.type)}
  <div class="param-value option-trigger relative">
    {value}

    <div class="option-value-container">
      {#each type_info.options as option}
        <button class="option-value" onclick={() => handleUpdate(option)}
          >{option}</button
        >
      {/each}
    </div>
  </div>
{:else if type_info.type === "string"}
  <div
    class="param-value"
    contenteditable
    onblur={(e: any) => {
      const new_value = e.target.innerText;
      if (new_value !== value) {
        handleUpdate(new_value);
      }
    }}
  >
    {value}
  </div>
{:else}
  <div class="param-value">{value}</div>
{/if}

<style lang="postcss">
  @reference "tailwindcss";
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
    @apply w-full text-center cursor-pointer hover:bg-gray-200 px-2;
  }
</style>
