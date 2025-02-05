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
    selection_card: string
    selection_container: string
    coordinate_as_dict: any
    dag: any
    zoom: any
    handleClick: Function
    constructor(svgId: string, node_radius: [number,number]=[100, 100], selection_card: string, selection_container: string) {
        this.svgId = svgId
        this.nodeRadius = node_radius
        this.line = d3.line().curve(d3.curveMonotoneY);
        this.dag = undefined;
        this.zoom = d3.zoom().scaleExtent([0.5, 32])
        .on("zoom", (e) => this.zoomed(e, this))
        .on("end", () => document.querySelectorAll(this.selection_card).forEach(div => div.style.transitionDuration = "0.5s"))

        this.selection_card = selection_card
        this.selection_container = selection_container
        this.coordinate_as_dict = {}
        this.handleClick = () => {}
    }
    init (handleClick=() => {}) {
        const svg = d3.select(`#${this.svgId}`)
        svg.append("g").attr("class", "links");
        svg.append("g").attr("class", "nodes");
        svg.append("g").attr("class", "bubbles");
        svg.call(this.zoom).call(this.zoom.transform, d3.zoomIdentity);
        this.handleClick = handleClick

        console.log("init done")
    }

    update(data: tNode[], expanded_nodes: string[]) {
        const self = this
        console.log("dag update", data)
        const svg = d3.select(`#${this.svgId}`);
        const svg_bbox = svg.node().getBoundingClientRect();
        svg.attr("viewBox", `0 0 ${svg_bbox.width} ${svg_bbox.height}`);
        const max_width = 1 * svg_bbox.width;
        const max_height = 1 * svg_bbox.height;
        const stratify = d3_dag.graphStratify();
        this.dag = stratify(data);


        const rect_size: [number, number] = [320, 250]
        const layout = d3_dag
        .sugiyama()
        // .grid()
        // .lane(d3_dag.laneOpt())
        // .coord(d3_dag.coordGreedy())
        // .nodeSize(this.nodeRadius)
        .nodeSize(rect_size)
        .gap([50, 50])
        // .tweaks([d3_dag.tweakSize({width: max_width, height: max_height})])
        // .tweaks([d3_dag.tweakShape(rect_size, d3_dag.shapeRect)])
        // .tweaks([d3_dag.tweakShape(rect_size, d3_dag.shapeRect), d3_dag.tweakSize({width: max_width, height: max_height})])

        const { width, height } = layout(this.dag);
        const translation_scaling = [max_width / width, 1.1*Math.max(1, max_height / height)]
        console.log({width, height, max_width, max_height})

        const vertical = true;
        this.coordinate_as_dict = Array.from(this.dag.nodes()).reduce((acc: any, d: any) => {
            acc[d.data.id] = {x: d.x * translation_scaling[0], y: d.y * translation_scaling[1]};
            return acc;
        }, {})

      // position nodes
      d3.selectAll(this.selection_card)
        .style("left", function() {
            const id = this.dataset.id
            const transform = d3.zoomTransform(svg.node())
            if(this.style.transform !== "") {
                return self.coordinate_as_dict[id].x - this.getBoundingClientRect().width / 2 / (transform.k === undefined? 1 : transform.k) + "px"
            } else {
                return self.coordinate_as_dict[id].x - this.getBoundingClientRect().width / 2 + "px"
            }
            // return coordinate_as_dict[id].x * (max_width / width) + "px";
            return vertical?
            self.coordinate_as_dict[id].x * (max_width / width) + "px":
            self.coordinate_as_dict[id].y * (max_width / height) + "px"

        })
        .style("top", function() {
            const id = this.dataset.id
            const transform = d3.zoomTransform(svg.node())
            if(this.style.transform !== "") {
                return self.coordinate_as_dict[id].y - this.getBoundingClientRect().height/ 2 / (transform.k === undefined? 1 : transform.k) + "px"
            } else {
                return self.coordinate_as_dict[id].y - this.getBoundingClientRect().height / 2 + "px"
            }
            return self.coordinate_as_dict[id].y * (max_height / height) + "px"
            return vertical ? 
            self.coordinate_as_dict[id].y * (max_height / height) + "px":
            self.coordinate_as_dict[id].x * (max_height / width) + "px"
        })
        .each(function() {
            applyTransform(this, d3.zoomTransform(svg.node()))
            this.style.transitionDuration = "0.5s"
        })
        // left: 376px;
//   top: 635.5px;
//   transform: translate(-684px, -814.5px) scale(0.5) translate(684px, 814.5px) translate(595px, 126px)

        svg.select("g.nodes")
        // .selectAll("rect.node")
            .data(Object.keys(self.coordinate_as_dict))
            .join(
                enter => enter.append("rect").attr("class", "node")
                        .attr("width",  0)
                        .attr("height",  0)
                        .attr("fill", "white")
                        .attr("stroke", "black")
                        .attr("stroke-width", 1)
                        .attr("rx", 10)
                        .attr("cursor", "pointer")
                        .attr("x", function(d) {
                            return self.coordinate_as_dict[d].x - rect_size[0]/2
                            // return coordinate_as_dict[d].x * (max_width / width) - rect_size[0]
                        })
                        .attr("y", function(d) {
                            return self.coordinate_as_dict[d].y - rect_size[1]/2
                            // return coordinate_as_dict[d].y * (max_height / height) - rect_size[1]
                        })
                        // .attr("x", ({ x }) => x * (max_width / width) - this.nodeRadius[0])
                        // .attr("y", ({ y }) => y * (max_height / height) - this.nodeRadius[1])
                        .on("click", (_, d) => {
                            // this.handleClick(d)
                            d3.selectAll(self.selection_card)
                            .nodes()
                            .filter((div_data) => div_data.dataset.id === d)[0].style.visibility = "visible"
                        })
                        .transition().duration(300)
                        .attr("width", rect_size[0])
                        .attr("height", rect_size[1])
                        ,
                update => update.transition().duration(500)
                        .attr("x", function(d) {
                            return self.coordinate_as_dict[d].x - rect_size[0]/2
                            // return coordinate_as_dict[d].x * (max_width / width) - rect_size[0]
                        })
                        .attr("y", function(d) {
                            return self.coordinate_as_dict[d].y - rect_size[1]/2
                            // return coordinate_as_dict[d].y * (max_height / height) - rect_size[1]
                        }),
                exit => exit.transition().duration(300)
                        .attr("width",  0)
                        .attr("height",  0)
                        .remove()
            )

        // plot edges

        this.update_links(translation_scaling)
        // plot edges between decomposed tasks
        const expansion_links = data.filter(d => expanded_nodes.includes(d.id)).map(d => {
            const first_child_coord = self.coordinate_as_dict[d.sub_tasks?.[0].id]
            console.log(d, first_child_coord)
            const this_coord = self.coordinate_as_dict[d.id]
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
        // svg.select("g.links")
        // .selectAll("path.expansion-link")
        // .data(expansion_links)
        // .join("path")
        // .attr("class", "expansion-link")
        // .attr("d", (d) => this.line(d))
        // .attr("fill", "none")
        // .attr("stroke-width", 3)
        // .attr("stroke", "gray")
        // .attr("stroke-dasharray", "5,5")

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

    update_links(translation_scaling) {
        const svg = d3.select(`#${this.svgId}`);
        svg.select("g.links")
            .selectAll("path.link")
            .data(this.dag.links(), ({source, target}) => `${source.data.id}-${target.data.id}`)
            .join("path")
            .transition().duration(500)
            .attr("class", "link")
            // .attr("d", (d) => this.line([node_positions[d.source.data.id], node_positions[d.target.data.id]]))
            // .attr("d", ({points}) => this.line(points.map(p => { return {x: p.x * translation_scaling[0], y: p.y * translation_scaling[1]}})))
            .attr("d", ({points}) => this.line(points.map(p => [p[0] * translation_scaling[0], p[1] * translation_scaling[1]])))
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

    zoomed(e, self) {
        const svg = d3.select(`#${self.svgId}`);
        svg.select("g.nodes").attr("transform", `translate(${e.transform.x}, ${e.transform.y}) scale(${e.transform.k})`);
        svg.select("g.links").attr("transform", `translate(${e.transform.x}, ${e.transform.y}) scale(${e.transform.k})`);
        document.querySelectorAll(self.selection_card).forEach(div => {
            applyTransform(div, e.transform)
            // div.style.transform = `scale(${e.transform.k})`
            // div.style.scale = e.transform.k
            // const left = parseFloat(div.style.left)
            // const top = parseFloat(div.style.top)
            // const width = div.getBoundingClientRect().width
            // const height = div.getBoundingClientRect().height
            // const offsetX = left + width / 2 / e.transform.k
            // const offsetY = top + height / 2 / e.transform.k
            // const transform = `translate(${-offsetX}px, ${-offsetY}px) scale(${e.transform.k}) translate(${offsetX}px, ${offsetY}px) translate(${e.transform.x / e.transform.k}px, ${e.transform.y / e.transform.k}px)`
            // div.style.transform = transform
        })
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

  function applyTransform(div, transform) {
    const left = parseFloat(div.style.left)
    const top = parseFloat(div.style.top)
    const width = div.getBoundingClientRect().width * (div.style.transform === ""? transform.k : 1)
    const height = div.getBoundingClientRect().height * (div.style.transform === ""? transform.k : 1)
    const offsetX = left + width / 2 / transform.k
    const offsetY = top + height / 2 / transform.k
    // console.log(div.dataset.id, div.style.transform, {left, top, width, height, offsetX, offsetY})
    const new_transform = `translate(${-offsetX}px, ${-offsetY}px) scale(${transform.k}) translate(${offsetX}px, ${offsetY}px) translate(${transform.x / transform.k}px, ${transform.y / transform.k}px)`
    div.style.transitionDuration = "0s"
    div.style.transform = new_transform
  }