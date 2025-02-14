<script lang="ts">
  import { onMount } from "svelte";
  import { scale } from "svelte/transition";
  import type { Snippet } from "svelte";
  import { evaluation_colors } from "constants";
  let {
    value,
    label,
    streaming,
    icon,
    handleToggle = () => {},
    show_transition = true,
  }: {
    value: boolean;
    label: string;
    streaming: boolean;
    icon: Snippet;
    handleToggle: Function;
    show_transition: boolean;
  } = $props();
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions, a11y_mouse_events_have_key_events (because of reasons) -->
<button
  class="p-1 rounded-full outline-gray-500 hover:outline-2 hover:scale-110 transition-all duration-100"
  class:disabled={streaming}
  style="background-color: {value
    ? evaluation_colors.good
    : evaluation_colors.bad}"
  onclick={() => {
    value = !value;
    handleToggle(value);
  }}
>
  {@render icon()}
</button>

<style lang="postcss">
  @reference "../app.css";
  .disabled {
    @apply cursor-not-allowed hover:scale-none hover:outline-none;
  }
</style>
