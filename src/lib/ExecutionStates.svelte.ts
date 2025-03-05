import type { tExecutionEvaluator, tPrimitiveTask } from 'types/server'
let evaluators: tExecutionEvaluator[] = $state([])
let primitiveTasks: tPrimitiveTask[] = $state([])
export const evaluatorState = {
    get evaluators() {
        return evaluators
    },
    set evaluators(value) {
        evaluators = value
    },
    updateEvaluator(name: string, evaluator: tExecutionEvaluator) {
        const index = evaluators.map(e => e.name).indexOf(name)
        if(index === -1) {
            evaluators[index] = evaluator
        }
    }
}

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
    updatePrimitiveTask(task_id: string, primitiveTask: tPrimitiveTask) {
        const index = primitiveTasks.map(t => t.id).indexOf(task_id)
        if(index !== -1) {
            primitiveTasks[index] = primitiveTask
        }
    }

}