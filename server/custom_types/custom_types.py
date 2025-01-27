from pydantic import BaseModel
from typing import TypedDict, Annotated
import operator


class Node(BaseModel):
    id: str
    label: str
    description: str
    explanation: str
    depend_on: list[str]
    parentIds: list[str]
    children: list["Node"] = []

    class Config:
        orm_mode = True


class BaseStateSchema(TypedDict):
    documents: Annotated[list, lambda a, b: b]
    entities: list


class ElementaryTaskDescription(BaseModel):
    id: str
    label: str
    description: str
    explanation: str
    parentIds: list[str]


class ElementaryTaskExecution(ElementaryTaskDescription):
    state_input_key: str
    doc_input_key: str
    state_output_key: str
    execution: str
