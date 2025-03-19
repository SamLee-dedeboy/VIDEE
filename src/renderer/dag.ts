import * as d3 from 'd3';
import * as d3_dag from 'd3-dag';
import type { tControllers, tNode } from 'types';
import type { SugiNode, SugiSeparation } from 'd3-dag';
import {
    BSplineShapeGenerator,
    ShapeSimplifier,
    BubbleSet,
    PointPath,
  } from 'bubblesets';

export class DAG {
    svgId: string;
    svgSize: [number, number];
    nodeRadius: [number,number];
    line: any
    selection_card: string
    selection_container: string
    bbox_dict: any
    dag: any
    zoom: any
    handleClick: Function
    updateGlobalLinks: Function | undefined
    next_expansion_id: string | undefined
    new_nodes: string[] = []
    constructor(svgId: string, node_radius: [number,number]=[100, 100], selection_card: string, selection_container: string) {
        this.svgId = svgId
        this.svgSize = [1000, 1000]
        this.nodeRadius = node_radius
        this.line = d3.line().curve(d3.curveMonotoneY);
        this.dag = undefined;
        this.zoom = d3.zoom().scaleExtent([0.5, 2])
        .on("zoom", (e) => this.zoomed(e, this))
        .on("end", () => document.querySelectorAll(this.selection_card).forEach((div: any) => div.style.transitionDuration = "0.5s"))

        this.selection_card = selection_card
        this.selection_container = selection_container
        this.bbox_dict = {}
        this.handleClick = () => {}
        this.updateGlobalLinks = undefined
    }
    init (updateGlobalLinks: Function=() => {}) {
        const svg = d3.select(`#${this.svgId}`)
        svg.append("g").attr("class", "next_expansion_link");
        svg.append("g").attr("class", "links");
        svg.append("g").attr("class", "nodes");
        // svg.append("g").attr("class", "bubbles");
        svg.call(this.zoom)
        // .call(this.zoom.transform, d3.zoomIdentity);
        // this.handleClick = handleClick
        this.updateGlobalLinks = updateGlobalLinks

        console.log("init done")
    }

    update(data: tNode[], max_value_path_ids: string[] = [], controllers?: tControllers, mcts=true, use_simplex=false, center_by_root=false) {
        const self = this
        console.log("dag update", data)
        const svg = d3.select(`#${this.svgId}`);
        const svg_bbox = svg.node().getBoundingClientRect();
        svg.attr("viewBox", `0 0 ${svg_bbox.width} ${svg_bbox.height}`);
        const max_width = 1 * svg_bbox.width;
        const max_height = 1 * svg_bbox.height;
        this.svgSize = [max_width, max_height]
        const stratify = d3_dag.graphStratify();
        this.dag = stratify(data);

        // const tweaks = vertical? [d3_dag.tweakFlip("diagonal")] : []
        const rect_size: [number, number] = this.nodeRadius
        const layout = use_simplex ? 
        d3_dag.sugiyama()
            // .layering(d3_dag.layeringTopological())
            // .coord(d3_dag.coordSimplex())
            .coord(this.customCoord(rect_size))
            .nodeSize((node: any) => {
                // return [(node.data.bbox?.width / 2.5 || rect_size[0]), (node.data.bbox?.height / 1.5 || rect_size[1])]
                return [(node.data.bbox?.width || rect_size[0]), (node.data.bbox?.height  || rect_size[1])]
            })
            .tweaks([ d3_dag.tweakFlip("diagonal")])
            .gap([50, 50])
        : d3_dag.sugiyama()
            .coord(d3_dag.coordQuad())
            .nodeSize((node: any) => {
                return [(node.data.bbox?.width || rect_size[0])  , (node.data.bbox?.height || rect_size[1])]
            })
            .gap([50, 50])
        console.log("layouting...")
        const { width, height } = layout(this.dag);

        this.bbox_dict = Array.from(this.dag.nodes()).reduce((acc: any, d: any) => {
            acc[d.data.id] = {x: d.x, y: d.y, width: d.data.bbox?.width || rect_size[0], height: d.data.bbox?.height || rect_size[1]};
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

            let enter_nodes: string[] = []
            svg.select("g.nodes")
            .selectAll("rect.node")
            .data(Object.keys(self.bbox_dict), (d) => d)
            .join(
                enter => enter.append("rect")
                        .attr("id", d => d)
                        .attr("class", "node")
                        .attr("width",  0)
                        .attr("height",  0)
                        .attr("fill", "oklch(0.985 0.002 247.839)")
                        .attr("rx", 10)
                        .attr("pointer-events", "none")
                        .attr("cursor", "pointer")
                        // .on("click", (_, d) => {
                        //     // this.handleClick(d)
                        //     d3.selectAll(self.selection_card)
                        //     .nodes()
                        //     .filter((div_data) => div_data.dataset.id === d)[0].style.visibility = "visible"
                        // })
                        // .transition().duration(300)
                        .attr("width", (d) => self.bbox_dict[d].width)
                        .attr("height", (d) => self.bbox_dict[d].height)
                        .each(function(d) {
                            enter_nodes.push(d)
                        })
                        .transition().duration(500)
                        .attr("x", function(d) {
                            return (self.bbox_dict[d].x - self.bbox_dict[d].width/2) 
                        })
                        .attr("y", function(d) {
                            return (self.bbox_dict[d].y - self.bbox_dict[d].height/2)
                        })
                        // .attr("width", rect_size[0])
                        // .attr("height", rect_size[1])
                        ,
                update => update.transition().duration(500)
                        .attr("width", (d) => self.bbox_dict[d].width)
                        .attr("height", (d) => self.bbox_dict[d].height)
                        .attr("x", function(d) {
                            return (self.bbox_dict[d].x - self.bbox_dict[d].width/2) 
                        })
                        .attr("y", function(d) {
                            return (self.bbox_dict[d].y - self.bbox_dict[d].height/2)
                        }),
                exit => exit.remove()
                )

        // plot edge        
        this.update_links(max_value_path_ids, controllers?.show_max_value_path, mcts)
        if(this.updateGlobalLinks !== undefined) {
            setTimeout(() => this.updateGlobalLinks(), 500)
        }


        // translate to make new nodes in the center
        if(enter_nodes.length !== 0) {
            if(center_by_root) {
                const roots = data.filter((d: any) => d.isRoot).map(d => d.id)
                enter_nodes = enter_nodes.filter((d) => roots.includes(d))
            }
            const new_nodes_bboxes = enter_nodes.map(d => self.bbox_dict[d])
            const new_nodes_center = [
                d3.mean(new_nodes_bboxes.map(d => d.x)),
                d3.mean(new_nodes_bboxes.map(d => d.y))
            ]
            // move the current zoom to the center of the new nodes
            svg.transition().duration(500).delay(0).call(this.zoom.translateTo, new_nodes_center[0], new_nodes_center[1])
            this.new_nodes = enter_nodes
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

    update_next_expansion_link(next_expansion_id: string | undefined) {
        console.log({next_expansion_id})
        this.next_expansion_id = next_expansion_id
        const svg = d3.select(`#${this.svgId}`);
        if(next_expansion_id && this.bbox_dict[next_expansion_id]) {
            const current_transform = d3.zoomTransform(svg.node())
            const next_expansion_group = svg.select("g.next_expansion_link")
            // next_expansion_group.selectAll("*").remove()
            const next_expansion_node = this.bbox_dict[next_expansion_id]
            // link from the next expansion node to the button with a line
            const next_expansion_node_position = current_transform.apply([next_expansion_node.x, next_expansion_node.y])
            next_expansion_group.selectAll("line.next_expansion_link")
                .data([0])
                .join("line")
                .attr("class", "next_expansion_link")
                // .transition().delay(500).duration(0)
                .attr("x1", next_expansion_node_position[0])
                .attr("y1", next_expansion_node_position[1])
                .attr("x2", this.svgSize[0]/2)
                .attr("y2", 10)
                .attr("fill", "none")
                .attr("stroke-width", 3)
                .attr("stroke", "oklch(0.705 0.213 47.604)")
                .attr("stroke-dasharray", "8,8")
        } else {
            svg.select("g.next_expansion_link").selectAll("*").remove()
        }

    }

    update_links(max_value_path_ids: string[] = [], show_max_value_path: boolean | undefined = false, mcts=true) {
        const svg = d3.select(`#${this.svgId}`);
        svg.select("g.links")
            .selectAll("path.link")
            .data(this.dag.links(), ({source, target}) => `${source.data.id}-${target.data.id}`)
            .join("path")
            .transition().duration(500)
            .attr("class", "link")
            .attr("d", ({points}) => this.line(points.map(p => [p[0], p[1]])))
            .attr("fill", "none")
            .attr("stroke-width", 2)
            .attr("stroke", "gray")
            .attr("stroke-dasharray", "8,8")
            .filter(({source, target}) => mcts && show_max_value_path && max_value_path_ids.includes(source.data.id) && max_value_path_ids.includes(target.data.id))
            .attr("stroke", "black")
            .attr("stroke-width", 4)
            .attr("stroke-dasharray", "unset")

    }


    zoomed(e, self) {
        const svg = d3.select(`#${self.svgId}`);
        svg.select("g.nodes").attr("transform", `translate(${e.transform.x}, ${e.transform.y}) scale(${e.transform.k})`);
        svg.select("g.links").attr("transform", `translate(${e.transform.x}, ${e.transform.y}) scale(${e.transform.k})`);
        // svg.select("g.next_expansion_link").attr("transform", `translate(${e.transform.x}, ${e.transform.y}) scale(${e.transform.k})`);
        document.querySelectorAll(self.selection_card).forEach(div => {
            applyTransform(div, e.transform)
        })

        const next_expansion_node = self.bbox_dict[self.next_expansion_id]
        if(next_expansion_node) {
            svg.select("g.next_expansion_link").select("line.next_expansion_link")
                .attr("x1", e.transform.apply([next_expansion_node.x, next_expansion_node.y])[0])
                .attr("y1", e.transform.apply([next_expansion_node.x, next_expansion_node.y])[1])
        }
        if(self.updateGlobalLinks) self.updateGlobalLinks()
    }
    resetTranslate() {
        const svg = d3.select(`#${this.svgId}`);
        const new_nodes_bboxes = this.new_nodes.map(d => this.bbox_dict[d])
        const new_nodes_center = [
            d3.mean(new_nodes_bboxes.map(d => d.x)),
            d3.mean(new_nodes_bboxes.map(d => d.y))
        ]
        // move the current zoom to the center of the new nodes
        svg.transition().duration(500).delay(0).call(this.zoom.translateTo, new_nodes_center[0], new_nodes_center[1])
        // svg.transition().duration(500).call(this.zoom.transform, d3.zoomIdentity);
    }
    customCoord (rect_size: [number, number]) {
        return function <N extends { x: number }, L>(layers: SugiNode<N, L>[][], sep: SugiSeparation<N, L>): number {
            // determine span of xs
            let min = Infinity;
            let max = -Infinity;
            for (const [layer_index, layer] of layers.entries()) {
                for (const [node_index, node] of layer.entries()) {
                    const { data } = node;
                    const x = node.x = layer_index * Math.max(100, rect_size[1]*1.1) + node_index * sep(layer[Math.max(0, node_index-1)], node);
                    min = Math.min(min, x - sep(undefined, node));
                    max = Math.max(max, x + sep(node, undefined));
                    // node.x -= min;
                }
            }
            for (const layer of layers) {
                for (const node of layer) {
                    node.x -= min;
                }
            }
            return max - min;
        }
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
