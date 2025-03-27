<script lang="ts">
  import { evaluation_colors } from "constants";
  import { onMount } from "svelte";
  import { likert_scale_num } from "lib/ExecutionStates.svelte";
  let { controllers, complexity_icon, coherence_icon, importance_icon } =
    $props();
  onMount(() => {
    evaluation_colors.create_color_scale_legend(
      document.querySelector(".color-scale-legend")
    );
  });
</script>

<div class="px-2 py-1 rouned flex gap-x-4">
  <div class="flex flex-col gap-y-1">
    <button
      class="evaluation-legend complexity"
      class:inactive={!controllers.show_complexity}
      class:no-interaction={true}
      onclick={() =>
        (controllers.show_complexity = !controllers.show_complexity)}
    >
      {@render complexity_icon()}
      <span> Complexity </span>
    </button>
    <button
      class="evaluation-legend coherence"
      class:inactive={!controllers.show_coherence}
      class:no-interaction={true}
      onclick={() => (controllers.show_coherence = !controllers.show_coherence)}
    >
      {@render coherence_icon()}
      <span> Coherence </span>
    </button>
    <button
      class="evaluation-legend importance"
      class:inactive={!controllers.show_importance}
      class:no-interaction={true}
      onclick={() =>
        (controllers.show_importance = !controllers.show_importance)}
    >
      {@render importance_icon()}
      <span> Importance </span>
    </button>
  </div>
  <div class="flex flex-col gap-y-2 justify-center">
    <div class="px-2 w-[12rem] h-[1rem]">
      <svg class="color-scale-legend w-full h-full overflow-visible"></svg>
    </div>
    <div class="flex justify-between gap-x-1 italic mt-1">
      {#each Array.from({ length: likert_scale_num + 1 }, (_, i) => i) as i}
        <div
          class="flex text-xs items-center gap-x-1 text-slate-600 select-none"
        >
          <svg class="w-6 h-6" viewBox="0 0 10 10">
            <circle
              cx="5"
              cy="5"
              r="5"
              fill={evaluation_colors.path_value_color_scale(
                i / likert_scale_num
              )}
            />
            <text
              x="5"
              y="5.3"
              text-anchor="middle"
              dominant-baseline="middle"
              fill="black"
              font-size="5"
            >
              {i + 1}
            </text>
          </svg>
          <!-- <span>{i}</span> -->
        </div>
      {/each}
    </div>
    <div class="flex justify-between gap-x-1 italic">
      <div class="flex text-xs items-center gap-x-1 text-slate-600 select-none">
        <!-- <svg class="w-6 h-6" viewBox="0 0 10 10">
      <circle cx="5" cy="5" r="5" fill={evaluation_colors.bad} />
    </svg> -->
        <span>Bad</span>
      </div>
      <div class="flex text-xs items-center gap-x-1 text-slate-600 select-none">
        <!-- <svg class="w-6 h-6" viewBox="0 0 10 10">
      <circle cx="5" cy="5" r="5" fill={evaluation_colors.good} />
    </svg> -->
        <span>Good</span>
      </div>
    </div>
  </div>
</div>

<style lang="postcss">
  @reference "tailwindcss";

  .evaluation-legend {
    @apply flex items-center px-2 py-1 rounded bg-white outline-2 outline-slate-700 text-xs text-slate-700 gap-x-1 max-w-[7.5rem];
  }
  .no-interaction {
    @apply pointer-events-none outline-none !bg-[unset] px-0;
  }
  .evaluation-legend:hover {
    @apply scale-110 transition-all;
  }
  .inactive {
    @apply opacity-40;
  }
</style>
