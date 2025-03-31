import { server_address } from 'constants'
import { getContext } from 'svelte'
import type { tSemanticTask, tExecutionEvaluator, tPrimitiveTask, tExecutionState } from 'types/server'

export let session_id: string = $state("312321321312321");
// let random_session_id = Math.random().toString(36).substring(2, 15);
export const likert_scale_num = 2;
let semantic_tasks: tSemanticTask[] = $state([])
let select_strategy: string = $state("UCT") // UCT, greedy

export const semanticTaskPlanState = {
    get semantic_tasks() {
        return semantic_tasks
    },
    set semantic_tasks(value) {
        semantic_tasks = value
    },
    get select_strategy() {
        return select_strategy
    },
    set select_strategy(value) {
        select_strategy = value
    },

    addTask() {
        if(semantic_tasks.length === 0) {
        semantic_tasks.push({
            id: "-1",
            label:  "Root",
            description: "Root",
            explanation: "N/A",
            parentIds: [],
            sub_tasks: [],
            children: [],
            // MCT types
            MCT_id: semantic_tasks.length.toString(),
            MCT_children_ids: [],
            MCT_parent_id: "",
            new_node: false,
            level: semantic_tasks.length,
            value: 0,
            visits: 0,
            path_value: 0,
            llm_evaluation: {
                complexity: likert_scale_num,
                coherence: likert_scale_num,
                importance: likert_scale_num,
                complexity_reason: "",
                coherence_reason: "",
                importance_reason: "",
              },
              user_evaluation: {
                complexity: likert_scale_num,
                coherence: likert_scale_num,
                importance: likert_scale_num,
                complexity_reason: "",
                coherence_reason: "",
                importance_reason: "",
              },
        });
        }
        semantic_tasks.push({
            id: Math.random().toString(),
            label: "New Task",
            description: "New Task Description",
            explanation: "N/A",
            parentIds: [],
            sub_tasks: [],
            children: [],
            // MCT types
            MCT_id: semantic_tasks.length.toString(),
            MCT_children_ids: [],
            MCT_parent_id: "",
            new_node: false,
            level: semantic_tasks.length,
            value: 0,
            visits: 0,
            path_value: 0,
            llm_evaluation: {
                complexity: likert_scale_num,
                coherence: likert_scale_num,
                importance: likert_scale_num,
                complexity_reason: "",
                coherence_reason: "",
                importance_reason: "",
              },
              user_evaluation: {
                complexity: likert_scale_num,
                coherence: likert_scale_num,
                importance: likert_scale_num,
                complexity_reason: "",
                coherence_reason: "",
                importance_reason: "",
              },
        });
        semantic_tasks = [...semantic_tasks]
    },

    deleteTask(task: tSemanticTask) {
        semantic_tasks = semantic_tasks.filter((_task) => _task.id !== task.id);
        const task_dict = semantic_tasks.reduce((acc, task) => {
        acc[task.id] = task;
        return acc;
        }, {});
        // update the parentIds of the children
        task.children.forEach((child_task_id) => {
        task_dict[child_task_id].parentIds = task_dict[
            child_task_id
        ].parentIds.filter((id) => id !== task.id);
        });

        // update the childrenIds of the parent
        task.parentIds.forEach((parent_task_id) => {
        task_dict[parent_task_id].children = task_dict[
            parent_task_id
        ].children.filter((id) => id !== task.id);
        });

    },

    addParent(task: tSemanticTask, parent_id: string) {
        task.parentIds = [...task.parentIds, parent_id]
        this.updateSemanticTask(task.id, task)
    },
    updateSemanticTask(task_id: string, semanticTask: tSemanticTask) {
        console.log("update task", task_id, semanticTask)
        const index = semantic_tasks.map(t => t.id).indexOf(task_id)
        if(index !== -1) {
            semantic_tasks[index] = semanticTask
        }
    }
}
let primitiveTasks: tPrimitiveTask[] = $state([])
let inspected_primitive_task_id: string | undefined = $state(undefined)
let inspected_primitive_task: tPrimitiveTask | undefined = $derived(inspected_primitive_task_id? primitiveTasks.find(t => t.id === inspected_primitive_task_id): undefined)
export const primitiveTaskState = {
    get primitiveTasks() {
        return primitiveTasks
    },
    set primitiveTasks(value) {
        // primitiveTasks = collectInputKeys(value)
        primitiveTasks = value
    },
    get inspected_primitive_task() {
        return inspected_primitive_task
    },
    addTask() {
        if(primitiveTasks.length === 0) {
            primitiveTasks.push(
            {
                solves: "",
                id: "-1",
                label: "Root",
                description: "Root",
                explanation: "N/A",
                parentIds: [],
                children: [],
            })
        }
        primitiveTasks.push(
            {
                solves: "",
                id: Math.random().toString(),
                label: "New Task",
                description: "New Task Description",
                explanation: "N/A",
                parentIds: [],
                children: [],
                recompile_needed_IO: false,
                recompile_needed_parameters: false,
            })
        primitiveTasks = [...primitiveTasks]
        // this.sortAndCollectInputKeys()
    },
    delete(task_id) {
        primitiveTasks = primitiveTasks.filter((_task) => _task.id !== task_id);
        primitiveTasks = primitiveTasks.map(t => {
            t.parentIds = t.parentIds.filter(id => id !== task_id)
            t.children = t.children.filter(id => id !== task_id)
            return t
        })

        if(task_id === inspected_primitive_task_id) {
            this.updateInspectedPrimitiveTask(undefined)
        }
        update_execution_with_server();
        // this.sortAndCollectInputKeys()
    },
    addParent(task: tPrimitiveTask, parent_id: string) {
        const parent_task = primitiveTasks.find(t => t.id === parent_id)
        if(parent_task) {
            task.parentIds = [...task.parentIds, parent_id]
            // primitiveTasks = sortNodesByHierarchy(primitiveTasks)
            // this.updatePrimitiveTask(task.id, task, false)
            parent_task.children = [...parent_task.children, task.id]
            primitiveTasks = sortNodesByHierarchy(primitiveTasks)
            this.updatePrimitiveTasks(primitiveTasks, true)
            // this.updatePrimitiveTask(parent_task.id, parent_task, true)
            // primitiveTasks = this.sortAndCollectInputKeys()
            // this.sortAndCollectInputKeys()
        }
    },
    removeParent(task: tPrimitiveTask, parent_id: string) {
        const parent_task = primitiveTasks.find(t => t.id === parent_id)
        if(parent_task) {
            task.parentIds = task.parentIds.filter(id => id !== parent_id)
            // primitiveTasks = sortNodesByHierarchy(primitiveTasks)
            // this.updatePrimitiveTask(task.id, task, false)
            parent_task.children = parent_task.children.filter(id => id !== task.id)
            primitiveTasks = sortNodesByHierarchy(primitiveTasks)
            this.updatePrimitiveTasks(primitiveTasks, true)
            // this.updatePrimitiveTask(parent_task.id, parent_task, true)
            // this.sortAndCollectInputKeys()
        }
    },
    updatePrimitiveTask(task_id: string, primitiveTask: tPrimitiveTask, needs_update=false, callback=() =>{}) {
        const index = primitiveTasks.map(t => t.id).indexOf(task_id)
        if(index !== -1) {
            primitiveTasks[index] = primitiveTask
            primitiveTasks = [...primitiveTasks]
            if(needs_update){
                update_execution_with_server(callback);
            }
        }
    },
    updatePrimitiveTasks(tasks: tPrimitiveTask[], needs_update=false) {
        primitiveTasks = [...tasks]
        if(needs_update){
            update_execution_with_server();
        }
    },
    // sortAndCollectInputKeys() {
    //     // sort the tasks by the parent-child relationships
    //     primitiveTasks = sortNodesByHierarchy(primitiveTasks)
    //     console.log("sorted tasks", primitiveTasks)
    //     // primitiveTasks = collectInputKeys(primitiveTasks)
    //     return primitiveTasks
    // },

    updateInspectedPrimitiveTask(task_id: string | undefined) {
        inspected_primitive_task_id = task_id
    },
    updateDocInputKeys(task_id: string, doc_input_keys: string[], needs_update=false) {
        const new_task = JSON.parse(JSON.stringify(primitiveTasks.find(t => t.id === task_id)))
        new_task.doc_input_keys = doc_input_keys
        if (new_task.execution.tool === "prompt_tool") {
            new_task.execution.parameters.prompt_template[1].content = `${new_task.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
        } else {
            new_task.recompile_needed_IO = false;
            new_task.recompile_needed_parameters = true;
        }
        this.updatePrimitiveTask(task_id, new_task, needs_update, () => {
            evaluators = collectTargetTaskKeys(evaluators, primitiveTasks)
        })
        // evaluators = collectTargetTaskKeys(evaluators, primitiveTasks)
    },
    updateOutputKey(task_id: string, output_key: string) {
        console.log("update output key", task_id, output_key)
        const index = primitiveTasks.map(t => t.id).indexOf(task_id)
        if(index !== -1) {
            const new_task = JSON.parse(JSON.stringify(primitiveTasks[index]))
            new_task.state_output_key = output_key
            // update the output key of the task
            primitiveTasks[index].state_output_key = output_key
            // update the input keys of the children
            // for(let primitive_task of primitiveTasks) {
            //     if(primitive_task.doc_input_keys?.includes(original_output_key)) {
            //         primitive_task.doc_input_keys = primitive_task.doc_input_keys?.map(key => key === original_output_key? output_key: key)
            //     }
            // }
            this.updatePrimitiveTask(task_id, new_task, true, () => {
                evaluators = collectTargetTaskKeys(evaluators, primitiveTasks)
            })
            // primitiveTasks = collectInputKeys(primitiveTasks)
            // update_execution_with_server(() => {
            // evaluators = collectTargetTaskKeys(evaluators, primitiveTasks)

            // });
        }
    }
}

function update_execution_with_server(callback=() => {}
) {
    fetch(`${server_address}/primitive_task/update/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ primitive_tasks: primitiveTasks, session_id }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Update primitive tasks success:", data);
        console.log(data);
        callback();
// Don't automatically reset recompile flags - they should persist until compilation
//         primitiveTasks.forEach(t => {
//             t.recompile_skip_IO = false
//             t.recompile_skip_parameters = false
//         })
        primitiveTaskState.primitiveTasks = data.primitive_tasks;
        // primitiveTaskExecutionStates.execution_states = data.execution_state;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
function sortNodesByHierarchy(nodes: { id: string; parentIds: string[]; children: string[] }[]) {
    const nodeMap = new Map();
    const inDegree = new Map();

    nodes.forEach(node => {
        nodeMap.set(node.id, node);
        inDegree.set(node.id, node.parentIds.length);
    });

    const queue = nodes.filter(node => inDegree.get(node.id) === 0);
    const sortedNodes: any[] = [];

    while (queue.length > 0) {
        const currentNode = queue.shift()!;
        sortedNodes.push(currentNode);

        currentNode.children.forEach(childId => {
            if (inDegree.has(childId)) {
                inDegree.set(childId, inDegree.get(childId) - 1);
                if (inDegree.get(childId) === 0) {
                    queue.push(nodeMap.get(childId));
                }
            }
        });
    }

    if (sortedNodes.length !== nodes.length) {
        throw new Error("Cycle detected in the graph, topological sort not possible.");
    }

    return sortedNodes;
}

function collectInputKeys(primitive_tasks: tPrimitiveTask[]) {
    let primitive_tasks_without_root = primitive_tasks.filter(t => t.id !== "-1")
    if(primitive_tasks_without_root.length === 0) return primitive_tasks
    if(primitive_tasks_without_root.some(t =>t.execution === undefined)) return primitive_tasks
    let existing_keys: Set<string> = new Set()
    primitive_tasks.forEach(primitive_task => {
        if(!primitive_task.doc_input_keys) return
        primitive_task.doc_input_keys.forEach(key => existing_keys.add(key))
        primitive_task.existing_keys = Array.from(existing_keys)
        existing_keys.add(primitive_task.state_output_key)
    })
    return primitive_tasks

}

let execution_states: Record<string, tExecutionState> | undefined = $state(undefined);
export const primitiveTaskExecutionStates = {
    get execution_states() {
        return execution_states
    },
    set execution_states(value) {
        execution_states = value
    },
    executable(task_id: string) {
        return execution_states?.[task_id]?.executable || false
    },
    executed(task_id: string) {
        return execution_states?.[task_id]?.executed || false
    }
}

let evaluators: tExecutionEvaluator[] = $state([])
let inspected_evaluator_name: string | undefined = $state(undefined)
let inspected_evaluator_node: tExecutionEvaluator | undefined = $derived(inspected_evaluator_name? evaluators.find(t => t.name === inspected_evaluator_name): undefined)
export const evaluatorState = {
    get evaluators() {
        return evaluators
    },
    set evaluators(value: tExecutionEvaluator[]) {
        // check and de-duplicate names
        let names: Record<string, number> = {}
        const primitive_task_ids = primitiveTasks.map(t => t.id)
        const primitive_task_id_index = primitive_task_ids.reduce((acc, id, index) => {
            acc[id] = index
            return acc
        }, {})

        evaluators = value.map((e, index) => {
            if(names[e.name]) {
                names[e.name] += 1
                e.name = e.name + "-" + names[e.name]
            } else {
                names[e.name] = 1
            }
            return e
        }).sort((a, b) => primitive_task_id_index[a.task] - primitive_task_id_index[b.task])

        let primitive_tasks_w_root: string[] = []
        evaluators.forEach(e => {
            const target_primitive_task = e.task
            if(primitive_tasks_w_root.includes(target_primitive_task)) {
                e.isRoot = false
                return
            }
            e.isRoot = true
            primitive_tasks_w_root.push(target_primitive_task)
        })

    },
    get inspected_evaluator_node() {
        return inspected_evaluator_node
    },
    updateEvaluator(name: string, evaluator: tExecutionEvaluator) {
        const index = evaluators.map(e => e.name).indexOf(name)
        console.log({name, evaluator, index})
        if(index !== -1) {
            evaluators[index] = evaluator
            evaluators = [...evaluators]
            console.log({evaluators})
        }
    },
    updateInspectedEvaluator(name: string | undefined) {
        inspected_evaluator_name = name
    }
}

function collectTargetTaskKeys(evaluators: tExecutionEvaluator[], primitiveTasks: tPrimitiveTask[]) {
    // update the input keys of the evaluators
    for(let evaluator of evaluators) {
        const target_task = primitiveTasks.find(t => t.id === evaluator.task)
        if(target_task) {
            evaluator.existing_keys = target_task.doc_input_keys?.concat([target_task.state_output_key])
            evaluator.doc_input_keys = evaluator.doc_input_keys?.filter(key => evaluator.existing_keys?.includes(key)) || []
            evaluator.parameters!.prompt_template[1].content = `${evaluator.doc_input_keys.map((key) => `${key}: {${key}}`).join("\n")}`;
        }
    }
    return evaluators
}
// function update_evaluator_with_server() {
//     fetch(`${server_address}/primitive_task/evaluators/update/`, {
//       method: "POST",
//       headers: {
//         "Content-Type": "application/json",
//       },
//       body: JSON.stringify({ primitive_tasks: primitiveTasks, session_id }),
//     })
//       .then((response) => response.json())
//       .then((data) => {
//         console.log("Update primitive tasks success:", data);
//         console.log(data);
//         primitiveTasks.forEach(t => {
//             // t.recompile_needed_IO = false
//             // t.recompile_needed_parameters = false
//         })
//         // primitiveTaskState.primitiveTasks = data.primitive_tasks;
//         // primitiveTaskExecutionStates.execution_states = data.execution_state;
//       })
//       .catch((error) => {
//         console.error("Error:", error);
//       });
//   }