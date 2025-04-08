from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from typing import Optional, List, Dict, Any, Callable
import json


def create_retryable_chain(chain, max_retries: int = 5):
    """
    Create a wrapper around a chain that retries the entire chain execution on failure.
    """

    def retry_chain_execution(inputs):
        # print(f"Executing chain with retry (max attempts: {max_retries})")
        attempts = 0
        last_error = None

        while attempts < max_retries:
            try:
                # Run the entire chain
                return chain.invoke(inputs)
            except Exception as e:
                last_error = e
                attempts += 1
                print(f"Chain execution attempt {attempts} failed: {str(e)}")
                if attempts >= max_retries:
                    print(f"All {max_retries} attempts failed")
                    break

        # If we get here, all attempts failed
        # Return empty dict instead of raising an exception to avoid breaking the flow
        print(f"Returning empty dict after {max_retries} failed attempts")
        return {}

    # Wrap the retry function as a Runnable
    return RunnableLambda(retry_chain_execution)


def prompt_tool(
    tool_name: str,
    prompt_template: list,
    model: str,
    api_key: str,
    format: str | None,
    max_retries: int = 5,
):
    template = ChatPromptTemplate(prompt_template)

    if format == "json":
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        # Build the base chain with JSON parsing
        json_parser = JsonOutputParser()
        base_chain = template | llm | json_parser

        # Wrap the entire chain with retry logic
        chain = create_retryable_chain(base_chain, max_retries=max_retries)
    else:
        llm = ChatOpenAI(model=model, api_key=api_key)
        # For non-JSON output, no need for special retry logic
        chain = template | llm | StrOutputParser()

    # Add the run name configuration
    chain = chain.with_config(run_name=tool_name)
    return chain


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
