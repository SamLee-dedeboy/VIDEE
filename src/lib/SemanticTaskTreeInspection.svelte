<script lang="ts">
  import { server_address } from "constants";
  import { slide } from "svelte/transition";
  import { onMount, setContext } from "svelte";
  import type {
    tDocument,
    tPrimitiveTaskDescription,
    tPrimitiveTaskExecution,
  } from "types";
  import { getContext } from "svelte";
  import Evaluator from "./Evaluator.svelte";
  import DatasetInspection from "./DatasetInspection.svelte";
  let { few_shot_examples }: { few_shot_examples: Record<string, any> } =
    $props();
  const session_id = (getContext("session_id") as Function)();
  let eval_definitions: Record<string, string> = $state({
    complexity: "The complexity of the task",
    coherence: "The coherence of the task",
    importance: "The importance of the task",
  });

  function getEvalDefinitions() {
    fetch(`${server_address}/eval/definitions/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log({ eval_definitions: data });
        eval_definitions = data;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function updateEvalDefinitions(_eval_definitions: Record<string, string>) {
    fetch(`${server_address}/eval/definitions/update/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ session_id, eval_definitions: _eval_definitions }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  onMount(() => {
    getEvalDefinitions();
  });
</script>

{#snippet complexity_icon()}
  <img src="network.svg" alt="complexity" class="w-6 h-6 pointer-events-none" />
{/snippet}

{#snippet coherence_icon()}
  <img src="waveform.svg" alt="coherence" class="w-6 h-6 pointer-events-none" />
{/snippet}

{#snippet importance_icon()}
  <img src="cpu.svg" alt="importance" class="w-6 h-6 pointer-events-none" />
{/snippet}

<div class="flex flex-col px-1 gap-y-4">
  <div class="flex flex-col gap-y-2">
    <DatasetInspection></DatasetInspection>
    <div
      class="text-[1.5rem] text-slate-600 font-semibold italic bg-gray-100 flex justify-center"
    >
      Task Evaluators
    </div>
    <Evaluator
      title="Complexity"
      definition={eval_definitions["complexity"]}
      icon={complexity_icon}
      few_shot_examples={few_shot_examples["complexity"]}
      handleDefinitionChanged={(new_definition) => {
        eval_definitions["complexity"] = new_definition;
        updateEvalDefinitions(eval_definitions);
      }}
    />
    <Evaluator
      title="Coherence"
      definition={eval_definitions["coherence"]}
      icon={coherence_icon}
      few_shot_examples={few_shot_examples["coherence"]}
      handleDefinitionChanged={(new_definition) => {
        eval_definitions["coherence"] = new_definition;
        updateEvalDefinitions(eval_definitions);
      }}
    />
    <Evaluator
      title="Importance"
      definition={eval_definitions["importance"]}
      icon={importance_icon}
      few_shot_examples={few_shot_examples["importance"]}
      handleDefinitionChanged={(new_definition) => {
        eval_definitions["importance"] = new_definition;
        updateEvalDefinitions(eval_definitions);
      }}
    />
  </div>
</div>

<style lang="postcss">
  @reference "../app.css";
  .header-2 {
    @apply text-lg font-bold font-mono text-slate-600 px-1 cursor-pointer hover:bg-gray-100 flex items-center border-b-2 border-slate-200 hover:border-2;
  }
</style>
