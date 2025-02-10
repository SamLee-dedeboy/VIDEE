export type tNode = {
    id: string;
    parentIds: string[];
    data: any;
    bbox?: DOMRect;
}
export type tSemanticTask = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    // depend_on: string[];
    parentIds: string[]
    children: string[];
    sub_tasks: tSemanticTask[] | undefined; 
    confidence: number;
    complexity: number;
}

export type tPrimitiveTaskDescription = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    parentIds: string[];
    children: string[];
    confidence: number;
    complexity: number;
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