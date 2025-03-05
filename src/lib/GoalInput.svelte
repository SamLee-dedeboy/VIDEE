<script lang="ts">
  let {
    user_goal = $bindable(""),
    mode = $bindable(),
    streaming_states,
    handleDecomposeGoal,
  }: {
    user_goal: string;
    mode: string;
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
    onblur={() => {
      const goal = document.querySelector(".goal-input")?.textContent || "";
      user_goal = goal;
      console.log("Goal changed to", goal);
    }}
  >
    I have a dataset of UIST paper abstracts. I want to extract high-level
    concepts from the abstracts to understand research topics and trends.
    <!-- I have a dataset of interview transcripts and I am going to do thematic
    analysis. Help me design a codebook, annotate the transcripts with the
    codebook, and then summarize findings -->
    <!-- I want to analyze media bias in news articles using knowledge graphs. -->
  </div>
  <div class="flex flex-col gap-y-1">
    <button
      class="mode-button text-sm flex items-center gap-x-2 hover:bg-gray-200 transition-all rounded px-1"
      onclick={() => (mode = mode === "streaming" ? "step" : "streaming")}
    >
      <span
        class="circle w-3 h-3 rounded-full outline outline-gray-600 transition-colors"
        data-attribute-mode={mode}
      ></span>
      Streaming Mode
    </button>
    <button
      class="grow outline-2 outline-green-300 bg-green-100 hover:bg-green-200 rounded px-2 flex items-center justify-center"
      class:disabled={running}
      onclick={() => {
        const goal = document.querySelector(".goal-input")?.textContent || "";
        user_goal = goal;
        handleDecomposeGoal(user_goal);
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
</div>

<style lang="postcss">
  @reference "../app.css";
  .disabled {
    @apply cursor-not-allowed bg-gray-300 outline-gray-200 opacity-50;
  }
  .circle[data-attribute-mode="streaming"] {
    @apply bg-green-300;
  }
  .circle[data-attribute-mode="step"] {
    @apply bg-white;
  }
  .mode-button:hover {
    & .circle {
    }
  }
</style>
