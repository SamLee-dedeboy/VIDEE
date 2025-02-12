<script lang="ts">
  let {
    streaming_states,
    handleDecomposeGoal,
  }: {
    streaming_states: {
      started: boolean;
      paused: boolean;
      finished: boolean;
    };
    handleDecomposeGoal: Function;
  } = $props();

  let idle = $derived(!streaming_states.started && !streaming_states.paused);
  let running = $derived(streaming_states.started && !streaming_states.paused);
  let paused = $derived(streaming_states.paused);
</script>

<div class="flex gap-x-2">
  <div
    class="goal-input outline-1 outline-gray-400 rounded shadow-md w-[30rem] h-[5rem] overflow-y-auto px-1 py-0.5"
    contenteditable
  >
    I need to construct a knowledge graph from a collection of documents from
    wikipedia.
  </div>
  <button
    class="outline-2 outline-green-300 bg-green-100 hover:bg-green-200 rounded px-2"
    class:disabled={running}
    onclick={() => {
      const goal = document.querySelector(".goal-input")?.textContent || "";
      handleDecomposeGoal(goal);
    }}
  >
    {#if paused}
      Continue
    {:else if running}
      <img
        src="loader_circle.svg"
        class="w-6 h-6 animate-spin opacity-50"
        alt="loading"
      />
    {:else if idle}
      Decompose
    {/if}
  </button>
</div>

<style lang="postcss">
  @reference "../app.css";
  .disabled {
    @apply cursor-not-allowed bg-gray-300 outline-gray-200 opacity-50;
  }
</style>
