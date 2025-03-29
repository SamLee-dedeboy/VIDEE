from pydantic import BaseModel, Field
from typing import TypedDict, Annotated, Any, Dict, List, Optional

# from typing import NotRequired


class SemanticTaskResponse(BaseModel):
    id: str
    label: str
    description: str
    explanation: str
    parentIds: list[str]


class Node(SemanticTaskResponse):
    children: list[str] = []
    sub_tasks: list["Node"] = []

    class Config:
        orm_mode = True


# class ScoreWithReasoning(BaseModel):
#     value: bool = False
#     reasoning: str = ""


class Evaluation(BaseModel):
    complexity: int = 0
    coherence: int = 0
    importance: int = 0
    complexity_reason: str = ""
    coherence_reason: str = ""
    importance_reason: str = ""


class MCT_Node(Node):
    print_label: str = "N/A"
    MCT_id: str
    MCT_parent_id: Optional[str]
    MCT_children_ids: list[str] = []
    visits: int = 0
    value: float = 0.0
    path_value: float = 1
    path_value_normalized: float = 1
    children_all_ends: bool = False
    level: int = 0
    new_node: bool = True
    llm_evaluation: Evaluation = Evaluation()
    user_evaluation: Evaluation = Evaluation()


class BaseStateSchema(TypedDict):
    documents: Annotated[list, lambda a, b: b]
    global_store: dict[str, Any] # a global storage for dynamic data (i.e. aggregated data on all docs)


class PrimitiveTaskDescription(BaseModel):
    id: str
    label: str
    description: str
    explanation: str
    parentIds: list[str]


class PrimitiveTaskExecution(PrimitiveTaskDescription):
    state_input_key: str
    doc_input_keys: list[str]
    state_output_key: str
    input_keys: list[str]
    execution: dict


class UserExecutionState(BaseModel):
    executable: bool