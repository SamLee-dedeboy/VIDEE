from pydantic import BaseModel


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


class ElementaryTaskDef(BaseModel):
    label: str
    definition: str
    input: str
    output: str
    example: dict
