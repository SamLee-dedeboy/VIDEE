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
        const index = semantic_tasks.map(t => t.id).indexOf(task_id)
        if(index !== -1) {
            semantic_tasks[index] = semanticTask
        }
    }
}
let evaluators: tExecutionEvaluator[] = $state([])
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
    updateEvaluator(name: string, evaluator: tExecutionEvaluator) {
        const index = evaluators.map(e => e.name).indexOf(name)
        if(index === -1) {
            evaluators[index] = evaluator
        }
    }
}

let primitiveTasks: tPrimitiveTask[] = $state([])
export const primitiveTaskState = {
    get primitiveTasks() {
        return primitiveTasks
    },
    set primitiveTasks(value) {
        primitiveTasks = value
    },
    add() {
        primitiveTasks = [
        ...primitiveTasks,
        {
            solves: "",
            id: Math.random().toString(),
            label: "New Task",
            description: "New Task Description",
            explanation: "N/A",
            parentIds: [],
            children: [],
        },
        ];
    },
    delete(task_id) {
        primitiveTasks = primitiveTasks.filter((_task) => _task.id !== task_id);
    },
    addParent(task: tPrimitiveTask, parent_id: string) {
        task.parentIds = [...task.parentIds, parent_id]
        this.updatePrimitiveTask(task.id, task)
    },
    updatePrimitiveTask(task_id: string, primitiveTask: tPrimitiveTask) {
        const index = primitiveTasks.map(t => t.id).indexOf(task_id)
        if(index !== -1) {
            primitiveTasks[index] = primitiveTask
        }
    }
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