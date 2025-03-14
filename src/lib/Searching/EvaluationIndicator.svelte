<script lang="ts">
  import { getContext, onMount } from "svelte";
  import { scale } from "svelte/transition";
  import type { Snippet } from "svelte";
  import { evaluation_colors } from "constants";
  import { trim } from "lib/trim";
  import type { tSemanticTask } from "types";
  let {
    task,
    value,
    llm_value,
    llm_reasoning,
    label,
    streaming = false,
    icon,
    handleToggle = () => {},
    show_transition = true,
  }: {
    task: tSemanticTask;
    value: boolean;
    llm_value: boolean;
    llm_reasoning: string;
    label: string;
    streaming?: boolean;
    icon: Snippet;
    handleToggle?: Function;
    show_transition: boolean;
  } = $props();
  $inspect(llm_reasoning);

  const setFewShotExampleExplanation: Function = getContext(
    "setFewShotExampleExplanation"
  );
  let asking_feedback = $state(false);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions, a11y_mouse_events_have_key_events (because of reasons) -->
<div class="flex relative font-mono z-10">
  <div class="indicator-button relative">
    <button
      class="p-1 relative rounded-full outline-gray-500 hover:outline-2 hover:scale-110 transition-all duration-100"
      title={label}
      class:disabled={streaming}
      style="background-color: {value
        ? evaluation_colors.good
        : evaluation_colors.bad}"
      onclick={() => {
        console.log(value, llm_value);
        value = !value;
        handleToggle(value);
        if (value !== llm_value) {
          asking_feedback = true;
        } else {
          asking_feedback = false;
        }
      }}
    >
      {@render icon()}
    </button>
    <div
      class="reasoning absolute hidden left-[calc(100%+5px)] top-0 text-xs rounded min-w-[18rem] max-w-[25rem] text-slate-600 flex-wrap text-left ml-[-0.5rem] pl-[0.5rem]"
    >
      <div
        class="outline-2 outline-gray-300 px-1 rounded bg-white flex flex-col"
      >
        <div
          class="w-full border-b border-gray-200 flex items-center justify-center py-0.5 gap-x-2 text-slate-800 font-semibold"
        >
          <img src="bot.svg" alt="bot" class="w-5 h-5" />
          Explanation by AI
        </div>
        <span class="font-thin">
          {llm_reasoning === undefined
            ? "No reasoning provided"
            : llm_reasoning}
        </span>
        <div class="font-semibold text-sm mt-1 inline px-1">
          If you disagree with the AI, click the icon to flip the score <img
            src="flip.svg"
            alt="flip"
            class="inline w-6 h-6"
          />
        </div>
      </div>
      {#if asking_feedback}
        <div
          class="input-box-container absolute left-[calc(100%+0px)] top-0 z-10 pl-1"
        >
          <div
            class=" bg-white shadow-md outline-2 outline-gray-400 rounded flex flex-col gap-y-1"
          >
            <div
              use:trim
              class="input-box px-2 min-w-[25rem] min-h-[2.5rem] text-sm text-gray-400 p-1 flex flex-wrap"
              contenteditable
              in:scale
            ></div>
            <div
              class="flex gap-x-2 text-sm self-center text-slate-600 mx-1 mb-1"
            >
              <button
                class="bg-green-100 px-1 py-0.5 rounded outline-2 outline-green-200"
                onclick={() => {
                  asking_feedback = false;
                  const explanation =
                    document.querySelector(".input-box")?.textContent;
                  setFewShotExampleExplanation(task, label, explanation);
                }}>Confirm</button
              >
              <button
                class="bg-gray-100 px-1 py-0.5 rounded outline-2 outline-gray-200"
                onclick={() => (asking_feedback = false)}>Close</button
              >
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .input-box:empty:before {
    content: "Why do you think this is good/bad?";
    cursor: text;
  }
  .indicator-button:hover > .reasoning {
    @apply flex;
  }
</style>
