export type tSemanticTask = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    // depend_on: string[];
    parentIds: string[]
    children: tSemanticTask[] | undefined; 
    confidence: number;
    complexity: number;
}

export type tPrimitiveTaskDescription = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    parentIds: string[]
}

export type tPrimitiveTaskExecution = tPrimitiveTaskDescription & {
    state_input_key: string,
    doc_input_keys: string[],
    state_output_key: any,
    execution: {
        tool: string,
        parameters: any
    }
}

export type tExecutionState = {
    executable: boolean,
}

export type tTask = tSemanticTask | tPrimitiveTaskDescription | tPrimitiveTaskExecution
export type tNode = { bbox?:DOMRect } & tTask