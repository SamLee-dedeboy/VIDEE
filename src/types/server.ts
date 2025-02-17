export type tNode = {
    id: string;
    parentIds: string[];
    data: any;
    bbox?: DOMRect;
}
export type tMCT_Node = {
    MCT_id: string;
    MCT_parent_id: string;
    MCT_children_ids: string[];
    level: number;
    llm_evaluation: {
        complexity: boolean;
        coherence: boolean;
        importance: boolean;
    }
    user_evaluation: {
        complexity: boolean;
        coherence: boolean;
        importance: boolean;
    }
    value: number;
    visits: number;
}

export type tSemanticTaskDescription = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    // depend_on: string[];
    parentIds: string[]
    children: string[];
    sub_tasks: tSemanticTask[] | undefined; 
} 
export type tSemanticTask = tSemanticTaskDescription & tMCT_Node

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