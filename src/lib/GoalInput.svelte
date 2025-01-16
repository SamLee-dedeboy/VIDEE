<script lang="ts">
  import { server_address } from "constants";
  let { semantic_tasks_fetched } = $props();
  function handleDecomposeGoal() {
    const goal = document.querySelector(".goal-input")?.textContent || "";
    fetch(`${server_address}/goal_decomposition/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ goal }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log({ data });
        semantic_tasks_fetched(data);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
</script>

<div
  class="flex flex-col gap-y-2 p-2 outline outline-1 outline-gray-200 shadow rounded"
>
  <div
    class="goal-input outline outline-1 outline-gray-400 rounded shadow-md min-h-[5rem] max-h-[8rem] overflow-y-auto px-1 py-0.5"
    contenteditable
  >
    I need to construct a knowledge graph from a collection of documents from
    wikipedia.
  </div>
  <button
    class="outline outline-2 outline-green-300 bg-green-100 hover:bg-green-200 rounded"
    onclick={handleDecomposeGoal}>Decompose</button
  >
</div>
