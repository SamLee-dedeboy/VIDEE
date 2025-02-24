import numpy as np
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from sklearn.cluster import KMeans


@tool
def calculator(operation: str, a: float, b: float) -> str:
    """Performs basic arithmetic operations: add, subtract, multiply, divide."""
    if operation == "add":
        return str(a + b)
    elif operation == "subtract":
        return str(a - b)
    elif operation == "multiply":
        return str(a * b)
    elif operation == "divide":
        if b == 0:
            return "Error: Division by zero"
        return str(a / b)
    else:
        return "Error: Invalid operation"

def clustering_tool(inputs: list[dict], n_clusters: int = 3, feature_key: str = "embedding"):
    """
    Creates a runnable that performs KMeans clustering on feature vectors extracted from inputs.

    Args:
        n_clusters (int): Number of clusters for KMeans (default: 3).
        feature_key (str): Key in each input dictionary containing the feature vector (default: "features").

    Returns:
        RunnableLambda: A runnable that takes a list of dicts and returns a list of cluster labels.
    """
    # Extract feature vectors from inputs
    data = [input[feature_key] for input in inputs]
    data_array = np.array(data)
    # Perform KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(data_array)
    return kmeans.labels_.tolist()


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
