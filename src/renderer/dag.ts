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
    bbox_dict: any
    dag: any
    zoom: any
    handleClick: Function
    constructor(svgId: string, node_radius: [number,number]=[100, 100], selection_card: string, selection_container: string) {
        this.svgId = svgId
        this.nodeRadius = node_radius
        this.line = d3.line().curve(d3.curveMonotoneY);
        this.dag = undefined;
        this.zoom = d3.zoom().scaleExtent([0.1, 32])
        .on("zoom", (e) => this.zoomed(e, this))
        .on("end", () => document.querySelectorAll(this.selection_card).forEach((div: any) => div.style.transitionDuration = "0.5s"))

        this.selection_card = selection_card
        this.selection_container = selection_container
        this.bbox_dict = {}
        this.handleClick = () => {}
    }
    init (handleClick=() => {}) {
        const svg = d3.select(`#${this.svgId}`)
        svg.append("g").attr("class", "links");
        svg.append("g").attr("class", "nodes");
        svg.append("g").attr("class", "bubbles");
        svg.call(this.zoom)
        // .call(this.zoom.transform, d3.zoomIdentity);
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


        // const rect_size: [number, number] = [320, 250]
        const rect_size: [number, number] = this.nodeRadius
        const layout = d3_dag
        .sugiyama()
        .coord(d3_dag.coordQuad())
        // .grid()
        // .lane(d3_dag.laneOpt())
        // .coord(d3_dag.coordGreedy())
        // .nodeSize(this.nodeRadius)
        .nodeSize((node: any) => {
            return [(node.data.bbox?.width || rect_size[0])  , (node.data.bbox?.height || rect_size[1])]
        })
        // .nodeSize(rect_size)
        .gap([50, 50])
        // .tweaks([d3_dag.tweakSize({width: max_width, height: max_height})])
        // .tweaks([d3_dag.tweakShape(rect_size, d3_dag.shapeRect)])
        // .tweaks([d3_dag.tweakShape(rect_size, d3_dag.shapeRect), d3_dag.tweakSize({width: max_width, height: max_height})])

        const { width, height } = layout(this.dag);
        // const translation_scaling = [Math.max(1, max_width / width), 1.1*Math.max(1, max_height / height)]
        const translation_scaling = [1, 1]
        console.log({width, height, max_width, max_height})

        this.bbox_dict = Array.from(this.dag.nodes()).reduce((acc: any, d: any) => {
            acc[d.data.id] = {x: d.x * translation_scaling[0], y: d.y * translation_scaling[1], width: d.data.bbox?.width || rect_size[0], height: d.data.bbox?.height || rect_size[1]};
            return acc;
        }, {})

      // position nodes
      d3.selectAll(this.selection_card)
        .style("left", function() { 
            const id = this.dataset.id
            return (self.bbox_dict[id].x - self.bbox_dict[id].width / 2) + "px"
        })
        .style("top", function() {
            const id = this.dataset.id
            return (self.bbox_dict[id].y - self.bbox_dict[id].height / 2)   + "px"
        })
        .each(function() {
            applyTransform(this, d3.zoomTransform(svg.node()))
            this.style.transitionDuration = "0.5s"
        })

        let new_nodes: any[] = []
        svg.select("g.nodes")
        .selectAll("rect.node")
            .data(Object.keys(self.bbox_dict), (d) => d)
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
                            return (self.bbox_dict[d].x - self.bbox_dict[d].width/2) 
                        })
                        .attr("y", function(d) {
                            return (self.bbox_dict[d].y - self.bbox_dict[d].height/2)
                        })
                        .on("click", (_, d) => {
                            // this.handleClick(d)
                            d3.selectAll(self.selection_card)
                            .nodes()
                            .filter((div_data) => div_data.dataset.id === d)[0].style.visibility = "visible"
                        })
                        // .transition().duration(300)
                        // .attr("width", (d) => self.bbox_dict[d].width)
                        // .attr("height", (d) => self.bbox_dict[d].height)
                        .each(function(d) {
                            new_nodes.push(d)
                        })
                        // .attr("width", rect_size[0])
                        // .attr("height", rect_size[1])
                        ,
                update => update.transition().duration(500)
                        .attr("x", function(d) {
                            return (self.bbox_dict[d].x - self.bbox_dict[d].width/2) / d3.zoomTransform(svg.node()).k
                            return self.bbox_dict[d].x - self.bbox_dict[d].width/2
                            return self.bbox_dict[d].x - rect_size[0]/2
                            // return bbox_dict[d].x * (max_width / width) - rect_size[0]
                        })
                        .attr("y", function(d) {
                            return (self.bbox_dict[d].y - self.bbox_dict[d].height/2) / d3.zoomTransform(svg.node()).k
                            return self.bbox_dict[d].y - self.bbox_dict[d].height/2
                            return self.bbox_dict[d].y - rect_size[1]/2
                            // return bbox_dict[d].y * (max_height / height) - rect_size[1]
                        }),
                exit => exit.transition().duration(300)
                        .attr("width",  0)
                        .attr("height",  0)
                        .remove()
                )

        // plot edges
        this.update_links(translation_scaling)

        // translate to make new nodes in the center
        if(new_nodes.length !== 0) {
            const new_nodes_bboxes = new_nodes.map(d => self.bbox_dict[d])
            const new_nodes_center = [
                d3.mean(new_nodes_bboxes.map(d => d.x)),
                d3.mean(new_nodes_bboxes.map(d => d.y))
            ]
            // move the current zoom to the center of the new nodes
            svg.transition().duration(500).delay(0).call(this.zoom.translateTo, new_nodes_center[0], new_nodes_center[1])

        }

        // plot edges between decomposed tasks
        // const expansion_links = data.filter(d => expanded_nodes.includes(d.id)).map(d => {
        //     const first_child_coord = self.bbox_dict[d.sub_tasks?.[0].id]
        //     console.log(d, first_child_coord)
        //     const this_coord = self.bbox_dict[d.id]
        //     const link_coords = vertical?
        //     [
        //         [this_coord.x * (max_width / width), this_coord.y * (max_height / height)],
        //         [first_child_coord.x * (max_width / width), first_child_coord.y * (max_height / height)]
        //     ]:
        //     [
        //         [this_coord.y * (max_width / height), this_coord.x * (max_height / width)],
        //         [first_child_coord.y * (max_width / height), first_child_coord.x * (max_height / width)]
        //     ]
        //     return link_coords
        // })
    }

    update_links(translation_scaling) {
        const svg = d3.select(`#${this.svgId}`);
        // const transform_scaling = transform === undefined? 1 : transform.k
        const transform_scaling = 1;
        svg.select("g.links")
            .selectAll("path.link")
            .data(this.dag.links(), ({source, target}) => `${source.data.id}-${target.data.id}`)
            .join("path")
            .transition().duration(500)
            .attr("class", "link")
            // .attr("d", (d) => this.line([node_positions[d.source.data.id], node_positions[d.target.data.id]]))
            // .attr("d", ({points}) => this.line(points.map(p => { return {x: p.x * translation_scaling[0], y: p.y * translation_scaling[1]}})))
            .attr("d", ({points}) => this.line(points.map(p => [p[0] * translation_scaling[0] / transform_scaling, p[1] * translation_scaling[1] / transform_scaling])))
            .attr("fill", "none")
            .attr("stroke-width", 3)
            .attr("stroke", "gray")
    }

    zoomed(e, self) {
        console.log("zoomed", e.transform)
        const svg = d3.select(`#${self.svgId}`);
        svg.select("g.nodes").attr("transform", `translate(${e.transform.x}, ${e.transform.y}) scale(${e.transform.k})`);
        svg.select("g.links").attr("transform", `translate(${e.transform.x}, ${e.transform.y}) scale(${e.transform.k})`);
        document.querySelectorAll(self.selection_card).forEach(div => {
            applyTransform(div, e.transform)
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
    const id = div.dataset.id
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