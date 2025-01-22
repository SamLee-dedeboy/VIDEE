export type tSemanticTask = {
    id: string;
    parentIds: string[]
    label: string;
    description: string;
    explanation: string;
    depend_on: string[];
    children: tSemanticTask[] | undefined; 
}

export type tElementaryTask = {
    id: string;
    parentIds: string[]
    label: string;
    description: string;
    explanation: string;
    depend_on: string[];
    children: tElementaryTask[] | undefined; 
}


export type tNode = { bbox?:DOMRect } & tSemanticTask