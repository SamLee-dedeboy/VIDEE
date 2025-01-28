export type tSemanticTask = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    // depend_on: string[];
    parentIds: string[]
    children: tSemanticTask[] | undefined; 
}

export type tElementaryTaskDescription = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    parentIds: string[]
}

export type tElementaryTaskExecution = tElementaryTaskDescription & {
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

export type tTask = tSemanticTask | tElementaryTaskDescription | tElementaryTaskExecution
export type tNode = { bbox?:DOMRect } & tTask