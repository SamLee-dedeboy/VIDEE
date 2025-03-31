<script lang="ts">
  import { server_address } from "constants";
  import { slide } from "svelte/transition";
  import { getContext, tick } from "svelte";
  import PagedDocuments from "./PagedDocuments.svelte";
  import SimplifiedListView from "./SimplifiedListView.svelte";
  import { session_id } from "lib/ExecutionStates.svelte";
  import type { tDocument } from "types";
  let { task_id }: { task_id: string } = $props();
  let show_result = $state(false);
  let result = $state<Record<string, any> | undefined>(undefined);
  let show_state_flags: Record<string, boolean> = $state({});
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
        show_state_flags = [
          "documents",
          ...Object.keys(result?.global_store || {}),
        ].reduce((acc, key) => {
          acc[key] = true;
          return acc;
        }, {});
        await tick();
        // document.querySelector(".result-panel")?.scrollIntoView({
        //   behavior: "smooth",
        //   block: "end",
        // });
        setTimeout(() => {
          const inspection_panel = document.querySelector(".inspection-panel");
          if (inspection_panel) {
            inspection_panel.scrollTo({
              top: inspection_panel.scrollHeight,
              behavior: "smooth",
            });
          }
        }, 100);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  export async function navigate_to_results() {
    show_result = true;
    handleFetchTaskResult();
  }

  // Check if the state value at the given key is a dictionary of lists
  function isDictionaryOfLists(value: any): boolean {
    if (!value || typeof value !== "object") return false;
    // Check if at least one key has an array value
    return Object.values(value).some((v) => Array.isArray(v));
  }

  // Check if the value is an array
  function isArray(value: any): value is any[] {
    return Array.isArray(value);
  }

  // Check if the list contains document objects (with at least id property)
  function isDocumentList(list: any[]): boolean {
    if (!list.length) return false;
    return typeof list[0] === "object" && list[0] !== null && "id" in list[0];
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
      <!-- documents -->
      <div class="flex flex-col state-container">
        <button
          class="state-key border-b-2 border-gray-200 italic text-slate-600 hover:bg-gray-200 shadow-xs"
          onclick={async (e: any) => {
            show_state_flags["documents"] = !show_state_flags["documents"];
            if (show_state_flags["documents"]) {
              await tick();
              const container = e.target.closest(".state-container");
              const state_content = container.querySelector(".state-content");
              state_content.classList.toggle("hide-state-content");
              state_content.scrollIntoView({
                behavior: "smooth",
                block: "center",
              });
            } else {
              setTimeout(() => {
                const inspection_panel =
                  document.querySelector(".inspection-panel");
                if (inspection_panel) {
                  inspection_panel.scrollTo({
                    top: inspection_panel.scrollHeight,
                    behavior: "smooth",
                  });
                }
              }, 100);
            }
          }}>documents</button
        >
        {#if show_state_flags["documents"]}
          <div in:slide class="state-content flex flex-col">
            <PagedDocuments
              documents={result.documents as tDocument[]}
              bg_color="oklch(0.97 0.014 254.604)"
              bg_hover_color="oklch(0.882 0.059 254.128)"
            />
          </div>
        {/if}
      </div>
      <!-- global stores -->
      {#each Object.keys(result.global_store) as state_input_key}
        {@const state_value = result.global_store[state_input_key]}
        <div class="flex flex-col state-container">
          <button
            class="state-key border-b-2 border-gray-200 italic text-slate-600 hover:bg-gray-200 shadow-xs"
            onclick={async (e: any) => {
              console.log(e.target);
              show_state_flags[state_input_key] =
                !show_state_flags[state_input_key];
              if (show_state_flags[state_input_key]) {
                await tick();
                const container = e.target.closest(".state-container");
                const state_content = container.querySelector(".state-content");
                state_content.classList.toggle("hide-state-content");
                state_content.scrollIntoView({
                  behavior: "smooth",
                  block: "center",
                });
              } else {
                setTimeout(() => {
                  const inspection_panel =
                    document.querySelector(".inspection-panel");
                  if (inspection_panel) {
                    inspection_panel.scrollTo({
                      top: inspection_panel.scrollHeight,
                      behavior: "smooth",
                    });
                  }
                }, 100);
              }
            }}>{state_input_key}</button
          >
          {#if show_state_flags[state_input_key]}
            <div in:slide class="state-content flex flex-col">
              {#if state_input_key === "global_store" && isDictionaryOfLists(state_value)}
                <!-- Special handling for global_store dictionary -->
                {#each state_value as documents}
                  <div class="global-store-container">
                    <!-- <div
                    class="dict-key border-b border-gray-300 bg-blue-50 px-2 py-1 text-slate-700 font-semibold"
                  >
                    {dictKey}
                  </div> -->
                    {#if isArray(documents) && documents.length > 0}
                      {#if isDocumentList(documents)}
                        <PagedDocuments
                          documents={documents as tDocument[]}
                          bg_color="oklch(0.97 0.014 254.604)"
                          bg_hover_color="oklch(0.882 0.059 254.128)"
                        />
                      {:else}
                        <SimplifiedListView
                          items={documents}
                          bg_color="oklch(0.97 0.014 254.604)"
                          bg_hover_color="oklch(0.882 0.059 254.128)"
                        />
                      {/if}
                    {:else}
                      <div class="p-2 text-gray-500 italic">No data</div>
                    {/if}
                  </div>
                {/each}
              {:else}
                <!-- Standard handling for regular arrays -->
                {#if isArray(state_value) && state_value.length > 0}
                  {#if isDocumentList(state_value)}
                    <PagedDocuments
                      documents={state_value as tDocument[]}
                      bg_color="oklch(0.97 0.014 254.604)"
                      bg_hover_color="oklch(0.882 0.059 254.128)"
                    />
                  {:else if ["embeddings", "embedding"].includes(state_input_key)}
                    <SimplifiedListView
                      items={state_value.slice(0, 10)}
                      bg_color="oklch(0.97 0.014 254.604)"
                      bg_hover_color="oklch(0.882 0.059 254.128)"
                    />
                    ...
                  {:else}
                    <SimplifiedListView
                      items={state_value}
                      bg_color="oklch(0.97 0.014 254.604)"
                      bg_hover_color="oklch(0.882 0.059 254.128)"
                    />
                  {/if}
                {:else}
                  <div class="p-2 text-gray-500 italic">
                    {state_value === null || state_value === undefined
                      ? "No data"
                      : typeof state_value === "object"
                        ? JSON.stringify(state_value)
                        : String(state_value)}
                  </div>
                {/if}
              {/if}
            </div>
          {/if}
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
  .global-store-container {
    @apply mb-6 border border-gray-200 rounded shadow-sm;
  }
</style>
