import * as d3 from "d3";
import type { tDRResult, tExecutionEvaluatorResult } from "types";
export class RadialEvaluationChart {
  svgId: string;
  width: number = 300;
  height: number = 300;
  padding = {
    left: 3,
    right: 3,
    top: 3,
    bottom: 3,
  };
  innerSize: {
    x: number;
    y: number;
    width: number;
    height: number;
    center: [number, number];
  } = {
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    center: [0, 0],
  };
  xScale: any;
  yScale: any;
  //   angleScale: any;
  polarRadiusScale: any;
  clusterColorScale: any;
  noiseColorScale: any;
  dispatch: any;
  constructor(svgId) {
    this.svgId = svgId;
  }
  init() {
    console.log("init");
    const svg = d3
      .select("#" + this.svgId)
      .attr("viewBox", `0 0 ${this.width} ${this.height}`);
    this.innerSize = {
      x: this.padding.left,
      y: this.padding.top,
      width: this.width - this.padding.left - this.padding.right,
      height: this.height - this.padding.top - this.padding.bottom,
      center: [
        this.padding.left + this.width / 2,
        this.padding.top + this.height / 2,
      ],
    };
    this.dispatch = d3.dispatch("force_end", "node_clicked");

    // this.noiseColorScale = d3.scaleSequential(d3.interpolateRainbow);
    this.noiseColorScale = () => "#c3c3c3";
    this.clusterColorScale = d3.scaleOrdinal(d3.schemeSet3);

    svg.append("g").attr("class", "participant-group");
    svg.append("g").attr("class", "node-group");
    svg.append("g").attr("class", "angle-axis-group");
    svg.append("g").attr("class", "legend-group");
    svg.append("g").attr("class", "cluster-label-group");
    svg.append("g").attr("class", "radius-axis-group");


    // .attr("stroke-dasharray", "5,5");
  }
  on(event, handler) {
    this.dispatch.on(event, handler);
  }
  update(data: tDRResult[], evaluation_result: tExecutionEvaluatorResult, highlight_ids: string[] | undefined, func_id = (d) => d.id, func_value = (d) => d.value) {
    const self = this;
    const svg = d3.select("#" + this.svgId);
    const circle_radius = 1.5
    const clusters = data
      .map((d) => d.cluster)
      .reduce((acc, cur) => {
        if (acc[cur] === undefined) {
          acc[cur] = 0;
        }
        acc[cur] += 1;
        return acc;
      }, {});
    const cluster_angles = computeAngles(clusters);
    const cluster_labels = data
      .map((d) => [d.cluster, d.cluster_label])
      .reduce((acc, cur) => {
        acc[cur[0]] = cur[1];
        return acc;
      }, {});
    
    this.polarRadiusScale = d3
      .scaleBand()
      .domain(evaluation_result.possible_scores)
      .range([30, Math.min(this.innerSize.width, this.innerSize.height) / 2]);

      // .scaleLinear()
      // .domain([0, 1])
      // .range([30, Math.min(this.innerSize.width, this.innerSize.height) / 2]);
    // update axis
    this.updateAxis(cluster_angles, evaluation_result.possible_scores);
    this.updateClusterLabels(cluster_angles, cluster_labels);

    const data_w_coordinates = data.map((datum) => {
      return {
        ...datum,
        coordinates_2d: polarToCartesian(
          self.innerSize.center,
          cluster_angles[datum.cluster].mid,
          // datum.angle,
          self.polarRadiusScale(func_value(datum)) - self.polarRadiusScale.bandwidth() / 2,
        ),
      };
    });

    const nodes = svg
      .select("g.node-group")
      .selectAll("circle.node")
      .data(data_w_coordinates, func_id)
      .join(
        (enter) => {
          const enter_nodes = enter
            .append("circle")
            .attr("class", "node")
            .classed("node-not-highlighted", false)
            .classed("node-highlighted", false)
            .attr("cx", (d) => (d.x = d.coordinates_2d[0]))
            .attr("cy", (d) => (d.y = d.coordinates_2d[1]))
            .attr("r", circle_radius)
            .attr("fill", (d) => this.clusterColorScale("" + d.cluster))
            .attr("stroke", "black")
            .attr("stroke-width", 0.5)
            .attr("cursor", "pointer")
            .on("click", function (e, d) {
              console.log("click", d);
              self.dispatch.call("node_clicked", null, d);
            })
          if (highlight_ids) {
            enter_nodes
              .classed("node-not-highlighted", true)
              .classed("node-highlighted", false)
              .filter((d) => highlight_ids.includes(d.id))
              .classed("node-not-highlighted", false)
              .classed("node-highlighted", true);
          }
          const simulation = d3
            .forceSimulation(data_w_coordinates)
            .alphaMin(0.10)
            .force(
              "radial",
              d3
                .forceRadial(
                  null,
                  this.innerSize.center[0],
                  this.innerSize.center[1],
                )
                .radius((d) => self.polarRadiusScale(func_value(d)) - self.polarRadiusScale.bandwidth() / 2)
                .strength(1),
            )
            .force(
              "collide",
              d3.forceCollide((d) => circle_radius * 1.3),
            )
            .on("tick", function () {
              enter_nodes.each(function (d) {
                d.x = clip(d.x, [
                  self.innerSize.x + circle_radius,
                  self.innerSize.x + self.innerSize.width - circle_radius,
                ]);
                d.y = clip(d.y, [
                  self.innerSize.y + circle_radius,
                  self.innerSize.y + self.innerSize.height - circle_radius,
                ]);
                [d.x, d.y] = clipClusterRange(
                  d.x,
                  d.y,
                  self.innerSize,
                  cluster_angles[d.cluster],
                );
                d3.select(this).attr("cx", d.x).attr("cy", d.y);
              });
            })
            .on("end", () => self.dispatch.call("force_end"));
        },
        (update) => {
          update
            .classed("node-not-highlighted", false)
            .classed("node-highlighted", false);
          if (highlight_ids) {
            update
              .classed("node-not-highlighted", true)
              .classed("node-highlighted", false)
              .filter((d) => highlight_ids.includes(d.id))
              .classed("node-not-highlighted", false)
              .classed("node-highlighted", true);
          }
          if (update.nodes().length > 0) {
            self.dispatch.call("force_end");
          }
        },
        (exit) => exit.remove(),
      );
  }
  clear() {
    const svg = d3.select("#" + this.svgId);
    svg.select("g.node-group").selectAll("circle.node").remove();
  }
  updateAxis(cluster_angles: Record<number, any>, possible_scores: string[]) {
    const svg = d3.select("#" + this.svgId);
    svg
      .select("g.radius-axis-group")
      .selectAll("circle")
      .data(possible_scores)
      .join("circle")
      .attr("cx", this.innerSize.center[0])
      .attr("cy", this.innerSize.center[1])
      .attr("r", (d) => this.polarRadiusScale(d))
      .attr("fill", "none")
      .attr("stroke", "lightgray")
      .attr("stroke-width", 1);
    svg
      .select("g.radius-axis-group")
      .selectAll("text")
      .data(possible_scores)
      .join("text")
      .text((d) => d)
      .attr("x", this.innerSize.center[0])
      .attr("y", (d) => this.innerSize.center[1] - this.polarRadiusScale(d) + this.polarRadiusScale.bandwidth() / 2)
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .attr("font-size", 10)
      .attr("fill", "#6d6d6d");
    const axis_group = svg.select("g.angle-axis-group");
    axis_group
      .selectAll("line")
      .data(Object.keys(cluster_angles))
      .join("line")
      .attr("x1", this.innerSize.center[0])
      .attr("y1", this.innerSize.center[1])
      .attr(
        "x2",
        (d) =>
          polarToCartesian(
            this.innerSize.center,
            cluster_angles[d].start,
            Math.min(this.innerSize.width, this.innerSize.height) / 2,
          )[0],
      )
      .attr(
        "y2",
        (d) =>
          polarToCartesian(
            this.innerSize.center,
            cluster_angles[d].start,
            Math.min(this.innerSize.width, this.innerSize.height) / 2,
          )[1],
      )
      .attr("stroke", "lightgray")
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "5,5");
    // axis_group
    //   .append("line")
    //   .attr("x1", this.innerSize.center[0])
    //   .attr("y1", this.innerSize.center[1])
    //   .attr(
    //     "x2",
    //     (d) =>
    //       polarToCartesian(
    //         this.innerSize.center,
    //         0,
    //         Math.min(this.innerSize.width, this.innerSize.height) / 2,
    //       )[0],
    //   )
    //   .attr(
    //     "y2",
    //     (d) =>
    //       polarToCartesian(
    //         this.innerSize.center,
    //         0,
    //         Math.min(this.innerSize.width, this.innerSize.height) / 2,
    //       )[1],
    //   )
    //   .attr("stroke", "black")
    //   .attr("stroke-width", 1)
    //   .attr("stroke-dasharray", "5,5");
  }

  updateClusterLabels(
    cluster_angles: Record<number, any>,
    cluster_labels: Record<number, string>,
  ) {
    const self = this
    const svg = d3.select("#" + this.svgId);
    const label_groups = svg.select("g.cluster-label-group");
    label_groups
      .selectAll("g.label-group")
      .data(Object.keys(cluster_angles))
      .join("g")
      .attr("class", "label-group")
      .each(function(d) {
        const group = d3.select(this);
        group.selectAll("text").remove();
        group.selectAll("rect").remove(); 
        group.selectAll("text")
          .data([d])
          .join("text")
          .attr("id", (d) => d)
          .text((d) => cluster_labels[d])
          .attr(
            "x",
            (d) =>
              polarToCartesian(
                self.innerSize.center,
                // cluster_angles[d].mid,
                cluster_angles[d].start + (cluster_angles[d].range * 1.1) / 2,
                Math.min(self.innerSize.width, self.innerSize.height) / 2.5,
              )[0]
          )
          .attr(
            "y",
            (d) =>
              polarToCartesian(
                self.innerSize.center,
                // cluster_angles[d].mid,
                cluster_angles[d].start + (cluster_angles[d].range * 1.1) / 2,
                Math.min(self.innerSize.width, self.innerSize.height) / 2.5,
              )[1],
          )
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "middle")
          .attr("font-size", 9)
          .attr("fill", (d) => darkenColor(self.clusterColorScale("" + d), 30))
          .attr("pointer-events", "none")
          .call(wrap, 100)
          .call(clipLabel, self.innerSize)
        const text_bboxes = group.selectAll("text").nodes().reduce((acc, cur) => {
          const bbox = cur.getBBox();
          acc[cur.getAttribute("id")] = bbox;;
          return acc;
        }, {});
        group.selectAll("rect")
          .data([d])
          .join("rect")
          .attr("x", (d) => text_bboxes[d].x - 3)
          .attr("y", (d) => text_bboxes[d].y - 1)
          .attr("width", (d) => text_bboxes[d].width + 6)
          .attr("height", (d) => text_bboxes[d].height + 3)
          .attr("fill", "white")
          .attr("stroke", "black")
          .attr("stroke-width", 0.5)
          .attr("opacity", 0.5)
          .lower()
      })
      .on("mouseover", function(e, d) {
        d3.select(this).raise();
      })
  }
}

function clipLabel(selection, bbox) {
  const node_bbox = selection.node().getBBox();
  const x = clip(node_bbox.x + node_bbox.width / 2, [bbox.x, bbox.x + bbox.width - node_bbox.width / 2]);
  const y = clip(node_bbox.y + node_bbox.height / 2, [bbox.y, bbox.y + bbox.height - node_bbox.height / 2]);
  selection.selectAll("tspan").attr("x", x).attr("y", y);
}

function clip(x, range) {
  return Math.max(Math.min(x, range[1]), range[0]);
}

function clipClusterRange(x, y, innerSize, cluster_angle) {
  //   console.log({ cluster_angle, innerSize });
  //   return [x, y];
  const [angle, radius] = cartesianToPolar(innerSize.center, x, y);
  const offset = Math.PI / 60;
  if (
    angle < cluster_angle.start + offset ||
    angle > cluster_angle.start + cluster_angle.range - offset
  ) {
    // increase radius
    const new_radius = radius + 10;
    const clipped_angle =
      Math.abs(angle - (cluster_angle.start + offset)) <
      Math.abs(angle - (cluster_angle.start + cluster_angle.range - offset))
        ? cluster_angle.start + 2 * offset
        : cluster_angle.start + cluster_angle.range - 2 * offset;
    const [new_x, new_y] = polarToCartesian(
      innerSize.center,
      clipped_angle,
      new_radius,
    );
    return [new_x, new_y];
  }
  return [x, y];
}

/**
 *
 * @param center [x, y]
 * @param angle
 * @param radius
 * @returns [x, y]
 */
function polarToCartesian(center, angle, radius) {
  return [
    center[0] + radius * Math.cos(angle),
    center[1] + radius * Math.sin(angle),
  ];
}

/**
 *
 * @param center [x, y]
 * @param x number
 * @param y number
 * @returns [angle, radius]
 */
function cartesianToPolar(center, x, y) {
  const adjustedX = x - center[0];
  const adjustedY = y - center[1];

  let theta = Math.atan2(adjustedY, adjustedX); // Calculate the angle in radians
  // Normalize theta to be in the range [0, 2π]
  if (theta < 0) {
    theta += 2 * Math.PI;
  }
  const r = Math.sqrt(adjustedX * adjustedX + adjustedY * adjustedY); // Calculate the radius

  return [theta, r];
}

function computeAngles(clusters: Record<number, number>) {
  const total = Object.values(clusters).reduce(
    (acc, cur) => acc + Math.sqrt(cur),
    0,
  );
  let offset = 0;
  const angles = Object.keys(clusters).reduce((acc, cur) => {
    const ratio = Math.sqrt(clusters[cur]) / total;
    const angle = ratio * Math.PI * 2;
    acc[cur] = {
      start: offset,
      range: ratio * Math.PI * 2,
      mid: offset + angle / 2,
    };
    offset += angle;
    return acc;
  }, {});
  return angles;
}

function darkenColor(hex, percent) {
  // Ensure the hex starts with #
  hex = hex.replace(/^#/, "");

  // Parse the red, green, and blue components
  let r = parseInt(hex.substring(0, 2), 16);
  let g = parseInt(hex.substring(2, 4), 16);
  let b = parseInt(hex.substring(4, 6), 16);

  // Calculate the new darker color
  r = Math.max(0, Math.floor(r * (1 - percent / 100)));
  g = Math.max(0, Math.floor(g * (1 - percent / 100)));
  b = Math.max(0, Math.floor(b * (1 - percent / 100)));

  // Convert back to hex and return
  const toHex = (value) => value.toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

// text longer than `width` will be in next line
function wrap(text, width) {
  text.each(function (d, i) {
      var text = d3.select(this),
          words = text.text().split(/\s+/).reverse(),
          word,
          line: any[] = [],
          lineNumber = 0,
          lineHeight = 1.1, // ems
          x = text.attr("x"),
          y = text.attr("y"),
          dy = 0, //parseFloat(text.attr("dy")),
          tspan = text.text(null)
              .append("tspan")
              .attr("x", x)
              .attr("y", y)
              .attr("dy", dy + "em")
              .attr("text-anchor", "bottom")
              .attr("dominant-baseline", "central")
      while (word = words.pop()) {
          line.push(word);
          tspan.text(line.join(" "));
          if (tspan.node()!.getComputedTextLength() > width && line.length > 1) {
              line.pop();
              tspan.text(line.join(" "));
              line = [word];
              tspan = text.append("tspan")
                  .attr("x", x)
                  .attr("y", y)
                  .attr("dy", ++lineNumber * lineHeight + dy + "em")
                  .attr("dominant-baseline", "central")
                  .text(word);
          }
  }
  const line_num = text.selectAll("tspan").nodes().length
  const em_to_px = 16
  text.selectAll("tspan").attr("y", parseFloat(y) - em_to_px / 2 * lineHeight * (line_num - 1) / 2)
});
}