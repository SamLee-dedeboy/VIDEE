from pydantic import BaseModel
from typing import TypedDict, Annotated
import operator


class Node(BaseModel):
    id: str
    label: str
    description: str
    explanation: str
    parentIds: list[str]
    children: list[str]
    sub_tasks: list["Node"] = []
    confidence: float
    complexity: float

    class Config:
        orm_mode = True


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
