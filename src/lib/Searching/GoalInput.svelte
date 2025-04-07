<script lang="ts">
  let {
    user_goal = $bindable(""),
    mode = $bindable(),
    disable_decompose,
    streaming_states,
    handleDecomposeGoal,
  }: {
    user_goal: string;
    mode: string;
    disable_decompose: boolean;
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
    <!-- I have a dataset of UIST paper abstracts. I want to extract high-level
    concepts from the abstracts. -->
    <!-- I have a dataset of interview transcripts and I am going to do thematic analysis.
    I want to develop a codebook from analysis of the corpus, and annotate the transcripts
    with the codebook. -->
    <!-- I want to analyze media bias in news articles using knowledge graphs. -->
    <!-- I want to generate high-level concepts from my dataset of UIST abstracts -->
    I have a dataset of customer comments and I want to analyze the dataset to discover
    interesting themes in customer feedback.
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
    <div
      class="grow outline-2 outline-green-300 bg-green-100 hover:bg-green-200 rounded px-2 flex items-center justify-center"
      class:disabled={running || disable_decompose}
    >
      <button
        class="w-full h-full flex items-center justify-center"
        class:disabled-button={running || disable_decompose}
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
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .disabled {
    @apply cursor-not-allowed bg-gray-300 outline-gray-200 opacity-50;
  }
  .disabled-button {
    @apply pointer-events-none;
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
