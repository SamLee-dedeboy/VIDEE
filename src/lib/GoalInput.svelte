<script lang="ts">
  let { handleDecomposeGoal }: { handleDecomposeGoal: Function } = $props();
</script>

<div class="flex gap-x-2">
  <div
    class="goal-input outline outline-1 outline-gray-400 rounded shadow-md min-h-[5rem] max-h-[8rem] overflow-y-auto px-1 py-0.5"
    contenteditable
  >
    I need to construct a knowledge graph from a collection of documents from
    wikipedia.
  </div>
  <button
    class="outline outline-2 outline-green-300 bg-green-100 hover:bg-green-200 rounded px-2"
    onclick={() => {
      const goal = document.querySelector(".goal-input")?.textContent || "";
      handleDecomposeGoal(goal);
    }}>Decompose</button
  >
</div>
