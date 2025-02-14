from pydantic import BaseModel
from typing import TypedDict, Annotated
from typing import Optional


class SemanticTaskResponse(BaseModel):
    id: str
    label: str
    description: str
    explanation: str
    parentIds: list[str]


class Node(SemanticTaskResponse):
    children: list[str]
    sub_tasks: list["Node"] = []

    class Config:
        orm_mode = True


class MCT_Node(SemanticTaskResponse):
    print_label: str = "N/A"
    MCT_id: str
    MCT_parent_id: Optional[str]
    MCT_children_ids: list[str] = []
    visits: int = 0
    value: float = 0.0
    children_all_ends: bool = False
    complexity: bool = False
    coherence: bool = False
    importance: bool = False


class BaseStateSchema(TypedDict):
    documents: Annotated[list, lambda a, b: b]
    entities: list


class PrimitiveTaskDescription(BaseModel):
    id: str
    label: str
    description: str
    explanation: str
    parentIds: list[str]


class PrimitiveTaskExecution(PrimitiveTaskDescription):
    state_input_key: str
    doc_input_key: str
    state_output_key: str
    execution: str


class UserExecutionState(BaseModel):
    executable: bool
