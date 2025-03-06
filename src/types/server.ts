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
    new_node: boolean;
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
    path_value: number;
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

export type tPrimitiveTask = tPrimitiveTaskDescription & Partial<tPrimitiveTaskExecution> 
export type tPrimitiveTaskDescription = {
    id: string;
    label: string;
    description: string;
    explanation: string;
    parentIds: string[];
    children: string[];
    solves: string;
}

export type tPrimitiveTaskExecution = {
    state_input_key: string,
    doc_input_keys: string[],
    state_output_key: any,
    execution: {
        tool: string,
        parameters: any
    }
}

export type tExecutionState = {
    executed: boolean,
    executable: boolean,
}

export type tTask = tSemanticTask | tPrimitiveTask

export type tExecutionEvaluator = {
    name: string;
    definition: string;
    task: string;
  } & Partial<tExecutionEvaluatorParams>;

export type tExecutionEvaluatorParams = {
    state_input_key: string;
    doc_input_keys: string[];
    state_output_key: string;
    parameters: {
      name: string;
      model: string;
      format: string;
      prompt_template: [
        {
          role: string;
          content: string;
        },
        {
          role: string;
          content: string;
        },
      ];
    };
  };