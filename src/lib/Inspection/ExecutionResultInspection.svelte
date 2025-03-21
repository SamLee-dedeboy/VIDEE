<script lang="ts">
  import { server_address } from "constants";
  import { slide } from "svelte/transition";
  import { getContext, tick } from "svelte";
  import PagedDocuments from "./PagedDocuments.svelte";
  import { session_id } from "lib/ExecutionStates.svelte";
  let { task_id }: { task_id: string } = $props();
  let show_result = $state(false);
  let result = $state(undefined);
  let fetching_result = $state(false);

  function handleFetchTaskResult() {
    fetching_result = true;
    fetch(`${server_address}/primitive_task/result/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ task_id, session_id }),
    })
      .then((response) => response.json())
      .then(async (data) => {
        console.log("Inspection fetched result:", data);
        result = data.result;
        fetching_result = false;
        await tick();
        document.querySelector(".result-panel")?.scrollIntoView({
          behavior: "smooth",
        });
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  export async function navigate_to_results() {
    show_result = true;
    handleFetchTaskResult();
  }
</script>

<div class="flex flex-col">
  <div class="flex flex-col">
    <button
      tabindex="0"
      class="header-2"
      onclick={async () => {
        show_result = !show_result;
        handleFetchTaskResult();
      }}
    >
      Result
      <img src="chevron_down.svg" alt="expand" class="hidden ml-auto w-5 h-5" />
    </button>
  </div>
  {#if fetching_result}
    <div class="flex justify-center items-center h-[5rem]">
      <img
        class="w-8 h-8 animate-spin"
        src="loader_circle.svg"
        alt="loading..."
      />
    </div>
  {/if}
  {#if show_result && result !== undefined}
    <div in:slide class="result-panel flex flex-col">
      {#each Object.keys(result) as state_input_key}
        <div class="flex flex-col state-container">
          <button
            class="state-key border-b-2 border-gray-200 italic text-slate-600 hover:bg-gray-200 shadow-xs"
            onclick={(e: any) => {
              console.log(e.target);
              const container = e.target.closest(".state-container");
              const state_content = container.querySelector(".state-content");
              state_content.classList.toggle("hide-state-content");
              state_content.scrollIntoView({ behavior: "smooth" });
            }}>{state_input_key}</button
          >
          <div class="state-content flex flex-col">
            <PagedDocuments
              documents={result[state_input_key]}
              bg_color="oklch(0.97 0.014 254.604)"
              bg_hover_color="oklch(0.882 0.059 254.128)"
            ></PagedDocuments>
          </div>
        </div>
      {/each}
    </div>
    <div class="h-[10rem]"></div>
  {/if}
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 bg-blue-100 px-1 cursor-pointer hover:bg-blue-200 flex items-center;
  }
  .header-2:hover > img {
    @apply block;
  }
  .hide-state-content {
    @apply hidden;
  }
</style>
