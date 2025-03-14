<script lang="ts">
  import type { tExecutionEvaluatorResult } from "types";
  import * as d3 from "d3";
  let { result }: { result: tExecutionEvaluatorResult } = $props();
  const svgId = "evaluator-result-svg";

  let barChartData: Record<string, number> = $derived.by(() => {
    console.log($state.snapshot(result));
    const evaluator_name = result.name;
    const evaluator_output_key = evaluator_name + "_output";
    const documents = result.result.documents;
    // const scores = documents.map((d) => d[evaluator_output_key]);
    const scores_count = documents.reduce(
      (acc, doc) => {
        const score = doc[evaluator_output_key];
        acc[score] += 1;
        return acc;
      },
      result.possible_scores.reduce((acc, score) => {
        acc[score] = 0;
        return acc;
      }, {})
    );
    // let scores_count = {};
    // scores.forEach((score) => {
    //   if (score in scores_count) {
    //     scores_count[score] += 1;
    //   } else {
    //     scores_count[score] = 1;
    //   }
    // });
    console.log(scores_count);
    return scores_count;
  });
  $effect(() => {
    updateBarChart(barChartData);
  });

  function updateBarChart(_barChartData: Record<string, number>) {
    const svg = d3.select(`#${svgId}`);
    const svgBbox = svg.node().getBoundingClientRect();
    const width = svgBbox.width;
    const height = svgBbox.height;
    const margin = { top: 20, right: 20, bottom: 30, left: 40 };
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    const colors = d3.scaleOrdinal(d3.schemePastel1);

    const x = d3
      .scaleBand()
      .range([margin.left, width - margin.left - margin.right])
      .padding(0.1);
    const y = d3.scaleLinear().range([height - margin.top, margin.bottom]);

    x.domain(Object.keys(_barChartData));
    y.domain([0, d3.max(Object.values(_barChartData))]);

    const bar_group = svg.select(".bar-group");

    bar_group
      .selectAll(".bar")
      .data(Object.keys(_barChartData))
      .join("rect")
      .attr("class", "bar")
      .attr("x", (d) => x(d))
      .attr("y", (d) => y(_barChartData[d]))
      .attr("fill", (d) => colors(d))
      .attr("width", x.bandwidth())
      .attr("height", (d) => height - margin.bottom - y(_barChartData[d]));

    const bar_label_group = svg.select(".bar-label-group");
    bar_label_group.selectAll(".bar-label").remove();
    bar_label_group
      .selectAll(".text")
      .data(Object.keys(_barChartData).filter((d) => _barChartData[d] > 0))
      .join("text")
      .attr("class", "bar-label")
      .attr("x", (d) => x(d) + x.bandwidth() / 2)
      .attr("y", (d, i) => y(_barChartData[d]) - 8)
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .text((d) => _barChartData[d]);

    svg.select(".axis-group").select(".x-axis").selectAll("*").remove();
    svg.select(".axis-group").select(".y-axis").selectAll("*").remove();
    svg
      .select(".axis-group")
      .select(".x-axis")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x));

    const yTickValues = d3.range(
      0,
      d3.max(Object.values(_barChartData)) + 1,
      1
    );
    svg
      .select(".axis-group")
      .select(".y-axis")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).tickValues(yTickValues).tickFormat(d3.format("d")));
  }
</script>

<div class="flex flex-col aspect-square bg-gray-50">
  <svg id={svgId} class="w-full h-full">
    <g class="bar-group"></g>
    <g class="bar-label-group"></g>
    <g class="axis-group">
      <g class="x-axis"></g>
      <g class="y-axis"></g>
    </g>
  </svg>
</div>
