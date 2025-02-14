<script lang="ts">
  import { onMount } from "svelte";
  import { scale } from "svelte/transition";
  import type { Snippet } from "svelte";
  let { value, label, icon }: { value: boolean; label: string; icon: Snippet } =
    $props();
  let component;
  let active_color = "lightgreen";
  let inactive_color = "#ffa2a2";
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions, a11y_mouse_events_have_key_events (because of reasons) -->
<button
  transition:scale
  bind:this={component}
  class="p-1 rounded-full outline-gray-500 hover:outline-2 hover:scale-110 transition-all duration-100"
  style="background-color: {value ? active_color : inactive_color}"
  onclick={() => (value = !value)}
>
  {@render icon()}
</button>

<style lang="postcss">
</style>
