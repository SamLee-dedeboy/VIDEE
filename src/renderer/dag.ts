import * as d3 from 'd3';
import * as d3_dag from 'd3-dag';
import type { tNode } from 'types';
import {
    BSplineShapeGenerator,
    ShapeSimplifier,
    BubbleSet,
    PointPath,
  } from 'bubblesets';

export class DAG {
    svgId: string;
    nodeRadius: [number,number];
    line: any
    dag: any
    constructor(svgId: string, node_radius: [number,number]=[100, 100]) {
        this.svgId = svgId
        this.nodeRadius = node_radius
        this.line = d3.line().curve(d3.curveMonotoneY);
        this.dag = undefined;
    }
    init () {
        const svg = d3.select(`#${this.svgId}`)
        svg.append("g").attr("class", "links");
        svg.append("g").attr("class", "bubbles");
        console.log("init done")
    }
    update(data: tNode[], expanded_nodes: string[], selection_query: string) {
        console.log("dag update", data)
        const svg = d3.select(`#${this.svgId}`);
        const svg_bbox = svg.node().getBoundingClientRect();
        svg.attr("viewBox", `0 0 ${svg_bbox.width} ${svg_bbox.height}`);
        const max_width = 1 * svg_bbox.width;
        const max_height = 1 * svg_bbox.height;
        const stratify = d3_dag.graphStratify();
        this.dag = stratify(data);


        const layout = d3_dag
        // .sugiyama()
        .grid()
        .lane(d3_dag.laneOpt())
        // .coord(d3_dag.coordGreedy())
        .nodeSize(this.nodeRadius)
        .gap([0, 0])

        const { width, height } = layout(this.dag);
        console.log()

        const vertical = true;
        const coordinate_as_dict: any = Array.from(this.dag.nodes()).reduce((acc: any, d: any) => {
            acc[d.data.id] = d;
            return acc;
        }, {})

      // position nodes
      d3.selectAll(selection_query)
        .style("left", function() {
            const id = this.dataset.id
            return coordinate_as_dict[id].x * (max_width / width) + "px";
            return vertical?
            coordinate_as_dict[id].x * (max_width / width) + "px":
            coordinate_as_dict[id].y * (max_width / height) + "px"

        })
        .style("top", function() {
            const id = this.dataset.id
            return coordinate_as_dict[id].y * (max_height / height) + "px"
            return vertical ? 
            coordinate_as_dict[id].y * (max_height / height) + "px":
            coordinate_as_dict[id].x * (max_height / width) + "px"
        })
        const self = this
        // svg.selectAll("rect.node")
        //     .data(Object.keys(coordinate_as_dict))
        //     .join("rect")
        //     .attr("class", "node")
        //     .attr("x", function(d) {
        //         return coordinate_as_dict[d].x * (max_width / width) - self.nodeRadius[0]
        //     })
        //     .attr("y", function(d) {
        //         return coordinate_as_dict[d].y * (max_height / height) - self.nodeRadius[1]
        //     })
        //     // .attr("x", ({ x }) => x * (max_width / width) - this.nodeRadius[0])
        //     // .attr("y", ({ y }) => y * (max_height / height) - this.nodeRadius[1])
        //     .attr("width",  this.nodeRadius[0] * 2)
        //     .attr("height",  this.nodeRadius[1] * 2)
        //     .attr("fill", "none")
        //     .attr("stroke", "black")
        //     .attr("stroke-width", 1)
        //     .attr("rx", 10)

        // plot edges

        this.update_links(selection_query)
        // plot edges between decomposed tasks
        const expansion_links = data.filter(d => expanded_nodes.includes(d.id)).map(d => {
            const first_child_coord = coordinate_as_dict[d.children?.[0].id]
            console.log(d, first_child_coord)
            const this_coord = coordinate_as_dict[d.id]
            const link_coords = vertical?
            [
                [this_coord.x * (max_width / width), this_coord.y * (max_height / height)],
                [first_child_coord.x * (max_width / width), first_child_coord.y * (max_height / height)]
            ]:
            [
                [this_coord.y * (max_width / height), this_coord.x * (max_height / width)],
                [first_child_coord.y * (max_width / height), first_child_coord.x * (max_height / width)]
            ]
            return link_coords
        })
        svg.select("g.links")
        .selectAll("path.expansion-link")
        .data(expansion_links)
        .join("path")
        .attr("class", "expansion-link")
        .attr("d", (d) => this.line(d))
        .attr("fill", "none")
        .attr("stroke-width", 3)
        .attr("stroke", "gray")
        .attr("stroke-dasharray", "5,5")

        // add bubbles
        return
        const bubble_group = svg.select("g.bubbles")
        const bubble_data = Object.groupBy(data, d => getGroup(d))
        bubble_group.selectAll("path.dag-wrapper").remove()
        Object.entries(bubble_data).forEach(([group, nodes]) => {
            const points = dag_to_screen_coord(nodes?.map(d => 
                [coordinate_as_dict[d.id].x, coordinate_as_dict[d.id].y]
            ) || [], max_width, max_height, width, height, vertical)
            console.log({nodes, points, coordinate_as_dict})
            const bubble_path = create_bubble_path(points, 1.3 * self.nodeRadius) 
            bubble_group.append("path")
                .attr("class", "dag-wrapper").attr("d", bubble_path)
                .attr("fill", "lightgreen")
                .attr("opacity", 0.2)
        })

    }

    update_links(selection_query) {
        const node_positions = d3.selectAll(selection_query).nodes().reduce((acc, node) => {
            acc[node.dataset.id] = [
                parseFloat(node.style.left),
                parseFloat(node.style.top)
            ]
            return acc
        }, {})
        const svg = d3.select(`#${this.svgId}`);
        svg.select("g.links")
            .selectAll("path.link")
            .data(this.dag.links())
            .join("path")
            .attr("class", "link")
            .attr("d", (d) => this.line([node_positions[d.source.data.id], node_positions[d.target.data.id]]))
            .attr("fill", "none")
            .attr("stroke-width", 3)
            .attr("stroke", "gray")
    }

    _update(data) {
        console.log({data})
        const svg = d3.select(`#${this.svgId}`)
        const svg_bbox = svg.node().getBoundingClientRect();
        svg.attr("viewBox", `0 0 ${svg_bbox.width} ${svg_bbox.height}`);
        const link_group = svg.select("g.links");
        const path_data = data.map((d) => {
            const to = d
            const dependencies = data.filter((d) => to.depend_on.includes(d.label));
            return dependencies.map((from) => {
                const x1 = from.bbox.x + from.bbox.width  - svg_bbox.x
                const y1 = from.bbox.y + from.bbox.height / 2 - svg_bbox.y
                const x2 = to.bbox.x - svg_bbox.x
                const y2 = to.bbox.y + to.bbox.height / 2 - svg_bbox.y
                let path = d3.path()
                path.moveTo(x1, y1);
                // path.bezierCurveTo(x1, y1 * 1.3, x2, y2 * 1.3, x2, y2);
                path.bezierCurveTo(x2, y1, x1, y2, x2, y2);
                // path.lineTo(x2, y2);
                return path.toString();
            })
        }).flat()
        link_group.selectAll("path")
            .data(path_data)
            .join("path")
            .attr("d", (d) => d)
            .attr("fill", "none")
            .attr("stroke", "black")

    }
}

function getGroup(node: tNode) {
    let id_parts = node.id.split("-")
    if(id_parts.length === 1) {
        return "root"
    }
    id_parts.pop()
    return id_parts.join("-")
}

function create_bubble_path(points, radius) {
    const pad = 0;
    // bubbles can be reused for subsequent runs or different sets of rectangles
    const bubbles = new BubbleSet();
  //   const first_point = points[0]
  //   const last_point = points[points.length - 1]
  //   console.log(first_point, last_point)
  //   const connector_point = [(first_point[0] + last_point[0])/2, (first_point[1] + last_point[1])/2]
  //   const closed_points = points.concat([connector_point])
      const closed_points = points
    // rectangles needs to be a list of objects of the form { x: 0, y: 0, width: 0, height: 0 }
    // lines needs to be a list of objects of the form { x1: 0, x2: 0, y1: 0, y2: 0 }
    // lines can be null to infer lines between rectangles automatically
    const rectangles = closed_points.map((point) => ({ x: point[0] - radius, y: point[1] - radius, width: 2*radius, height: 2*radius }));
    const list = bubbles.createOutline(
      BubbleSet.addPadding(rectangles, pad),
      [],
      null /* lines */
    );
    // outline is a path that can be used for the attribute d of a SVG path element
    const outline = new PointPath(list).transform([
      new ShapeSimplifier(0.0),  // removes path points by removing (near) colinear points
      new BSplineShapeGenerator(),  // smoothes the output shape using b-splines
      new ShapeSimplifier(0.0),  // removes path points by removing (near) colinear points
    ]);
    return outline
  }

  function dag_to_screen_coord(
        dag_points: [number, number][],
        max_width: number,
        max_height: number,
        width: number,
        height: number,
        vertical: boolean,
  ) {
    return dag_points.map(p => vertical?
        [p[0] * (max_width / width), p[1] * (max_height / height)]
        :
        [p[1] * (max_width / height), p[0] * (max_height / width)]
    )
  }