import type { tSemanticTask, tExecutionEvaluator, tPrimitiveTask, tExecutionState } from 'types/server'
let semantic_tasks: tSemanticTask[] = $state([])

export const semanticTaskPlanState = {
    get semantic_tasks() {
        return semantic_tasks
    },
    set semantic_tasks(value) {
        semantic_tasks = value
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
                complexity: true,
                coherence: true,
                importance: true,
                complexity_reason: "",
                coherence_reason: "",
                importance_reason: "",
              },
              user_evaluation: {
                complexity: true,
                coherence: true,
                importance: true,
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
                complexity: true,
                coherence: true,
                importance: true,
                complexity_reason: "",
                coherence_reason: "",
                importance_reason: "",
              },
              user_evaluation: {
                complexity: true,
                coherence: true,
                importance: true,
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
        if(index === -1) {
            evaluators[index] = evaluator
        }
    },
    updateInspectedEvaluator(name: string | undefined) {
        inspected_evaluator_name = name
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
        primitiveTasks = value
        primitiveTasks = collectInputKeys(primitiveTasks)
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
            })
        primitiveTasks = [...primitiveTasks]
        console.log({primitiveTasks})
    },
    delete(task_id) {
        primitiveTasks = primitiveTasks.filter((_task) => _task.id !== task_id);
    },
    addParent(task: tPrimitiveTask, parent_id: string) {
        task.parentIds = [...task.parentIds, parent_id]
        this.updatePrimitiveTask(task.id, task)

        const parent_task = primitiveTasks.find(t => t.id === parent_id)
        if(parent_task) {
            parent_task.children = [...parent_task.children, task.id]
            this.updatePrimitiveTask(parent_task.id, parent_task)
        }
    },
    updatePrimitiveTask(task_id: string, primitiveTask: tPrimitiveTask) {
        const index = primitiveTasks.map(t => t.id).indexOf(task_id)
        console.log("update task", task_id, index, primitiveTask)
        if(index !== -1) {
            primitiveTasks[index] = primitiveTask
            primitiveTasks = [...primitiveTasks]
            primitiveTasks = collectInputKeys(primitiveTasks)
        }
    },
    updateInspectedPrimitiveTask(task_id: string | undefined) {
        inspected_primitive_task_id = task_id
    },
    updateOutputKey(task_id: string, output_key: string) {
        console.log("update output key", task_id, output_key)
        const index = primitiveTasks.map(t => t.id).indexOf(task_id)
        if(index !== -1) {
            const original_output_key = primitiveTasks[index].state_output_key
            primitiveTasks[index].state_output_key = output_key
            for(let primitive_task of primitiveTasks) {
                if(primitive_task.doc_input_keys?.includes(original_output_key)) {
                    primitive_task.doc_input_keys = primitive_task.doc_input_keys?.map(key => key === original_output_key? output_key: key)
                }
            }
            primitiveTasks = collectInputKeys(primitiveTasks)
        }
    }
}

function collectInputKeys(primitive_tasks: tPrimitiveTask[]) {
    if(primitive_tasks.length === 0) return primitive_tasks
    if(primitive_tasks.some(t =>t.execution === undefined)) return primitive_tasks
    let existing_keys: Set<string> = new Set()
    for(let primitive_task of primitive_tasks) {
        primitive_task.existing_keys = Array.from(existing_keys)
        primitive_task.doc_input_keys?.forEach(key => existing_keys.add(key))
        existing_keys.add(primitive_task.state_output_key)
    }
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