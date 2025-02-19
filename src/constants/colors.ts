import * as d3 from "d3"


const good_color = "#7bf1a8"
const bad_color = "#ffa2a2"
export const evaluation_colors = {
    good: good_color,
    bad: bad_color,
    // path_value_color_scale: d3.scaleSequential(d3.interpolateRgb(bad_color, good_color)).domain([0, 1]),
    // path_value_color_scale: d3.scaleDiverging(d3.interpolateRgb(bad_color, good_color)),
    path_value_color_scale: d3.scaleDiverging([bad_color, "#eae713", good_color]),
    create_color_scale_legend: create_color_scale_legend
}

export function create_color_scale_legend(svg) {
    const width = svg.getBoundingClientRect().width
    const height = svg.getBoundingClientRect().height
    svg = d3.select(svg)
    svg.selectAll("*").remove();
    let sequentialScale = evaluation_colors.path_value_color_scale  
    const group = svg.append("g")
        .attr("class", "legendSequential")
    
    const cells = 10
    const offset = 2
    const cell_width = (width - (cells-1)*offset) / cells
    group.selectAll("rect")
    .data(d3.range(cells))
    .join("rect")
    .attr("width", cell_width)
    .attr("height", height/2)
    .attr("x", (d, i) => i * (cell_width+offset))
    .attr("y", 0)
    .attr("fill", d => sequentialScale(d / cells))
    group.append("text")
    .attr("x", 0)
    .attr("y", height/2 + 3)
    .text("0")
    .attr("font-size", "0.7rem")
    .attr("dominant-baseline", "hanging")
    .attr("text-anchor", "start")
    .attr("font-style", "italic")
    group.append("text")
    .attr("x", width/2)
    .attr("y", height/2 + 3)
    .text("0.5")
    .attr("font-size", "0.7rem")
    .attr("dominant-baseline", "hanging")
    .attr("text-anchor", "middle")
    .attr("font-style", "italic")
    group.append("text")
    .attr("x", width)
    .attr("y", height/2 + 3)
    .text("1")
    .attr("font-size", "0.7rem")
    .attr("dominant-baseline", "hanging")
    .attr("text-anchor", "end")
    .attr("font-style", "italic")
                
}
