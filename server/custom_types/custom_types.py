from pydantic import BaseModel
from typing import TypedDict


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
    documents: list
    entities: list


class ElementaryTaskDef(BaseModel):
    id: str
    label: str
    definition: str
    state_input_key: str
    doc_input_key: str
    state_output_key: str
    parentIds: list[str]
    execution: str
    # input: str
    # output: str
    # example: dict
