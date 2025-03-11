from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser


def prompt_tool(
    tool_name: str,
    prompt_template: list,
    model: str,
    api_key: str,
    format: str | None,
):
    template = ChatPromptTemplate(prompt_template)
    llm_chain = template | ChatOpenAI(model=model, api_key=api_key)
    if format == "json":
        llm_chain = llm_chain | JsonOutputParser()
    else:
        llm_chain = llm_chain | StrOutputParser()
    llm_chain = llm_chain.with_config(run_name=tool_name)
    return llm_chain


# template must have the following structure:
# [
#     {
#         "role": "system", (role could differ)
#         "content": "Hello, how can I help you today?"
#     },
#     {
#         "role": "human", (role could differ)
#         "content": "I need help with my computer."
#     },
#    ...
# ]
def parse_template(template: list[dict]):
    res = [(message["role"], message["content"]) for message in template]
    return res