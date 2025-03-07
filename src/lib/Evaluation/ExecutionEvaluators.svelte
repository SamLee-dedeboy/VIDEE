<script lang="ts">
  import { server_address } from "constants";
  import { getContext } from "svelte";
  import ExecutionEvaluatorCard from "./ExecutionEvaluatorCard.svelte";
  import { trim } from "lib/trim";
  import type {
    tExecutionEvaluator,
    tPrimitiveTaskDescription,
    tSemanticTaskDescription,
  } from "types";
  import AddExecutionEvaluator from "../Execution/AddExecutionEvaluator.svelte";

  let {
    tasks,
  }: { tasks: tPrimitiveTaskDescription[] | tSemanticTaskDescription[] } =
    $props();

  const session_id = (getContext("session_id") as Function)();
  let loading = $state(false);
  let adding_evaluator = $state(false);
  let evaluators: tExecutionEvaluator[] = $state([]);

  function handleAddEvaluator() {
    adding_evaluator = true;
    // evaluators = [
    //   ...evaluators,
    //   {
    //     name: "",
    //     description: "",
    //     task: tasks[0].id as string,
    //   },
    // ];
  }

  function handleGenerateEvaluator(description: string, task_id: string) {
    adding_evaluator = false;
    loading = true;
    console.log(
      "Generating evaluator",
      description,
      tasks.find((t) => t.id === task_id),
      session_id
    );
    fetch(`${server_address}/primitive_task/evaluators/add/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        task: tasks.find((t) => t.id === task_id),
        description,
        session_id,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
        evaluators.push(data["result"]);
        loading = false;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
</script>

<div class="flex flex-col gap-y-2">
  <div
    class="header-1 text-[1.5rem] text-slate-600 font-semibold italic flex justify-center"
  >
    Result Evaluators
  </div>
  <div class="flex flex-col gap-y-2">
    {#each evaluators as evaluator, index}
      <ExecutionEvaluatorCard
        bind:evaluator={evaluators[index]}
        {loading}
        tasks={tasks
          .filter((t) => t.label !== "Root")
          .map((t) => [t.id as string, t.label as string])}
        handleDelete={() => {
          evaluators = evaluators.filter((e) => e !== evaluator);
        }}
      ></ExecutionEvaluatorCard>
    {/each}
  </div>
  {#if adding_evaluator}
    <AddExecutionEvaluator
      tasks={tasks
        .filter((t) => t.label !== "Root")
        .map((t) => [t.id as string, t.label as string])}
      {handleGenerateEvaluator}
    ></AddExecutionEvaluator>
  {/if}
  {#if loading}
    <div class="flex w-full justify-center items-center">
      <img src="loader_circle.svg" alt="loading" class="w-6 h-6 animate-spin" />
    </div>
  {:else}
    <button
      class="w-full hover:bg-gray-100 flex justify-center py-2 rounded"
      onclick={handleAddEvaluator}
    >
      <div class="rounded-full p-0.5 outline-[1.5px] outline-gray-800">
        <img src="plus.svg" class="w-4 h-4" alt="add" />
      </div>
    </button>
  {/if}
</div>

<style lang="postcss">
  @reference "tailwindcss";
  .header-1 {
    background-color: var(--bg-color);
  }
</style>
