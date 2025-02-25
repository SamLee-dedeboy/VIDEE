from openai import OpenAI

def embedding_tool(doc: dict, api_key: str, model: str = "text-embedding-ada-002", feature_key: str = "embedding") -> list[float]:
    """
    Generates an embedding for the given text using OpenAI's embedding model.

    Args:
        doc: single document
        api_key: api key
        model (str): The embedding model to use (default: "text-embedding-ada-002").
        feature_key: Key in the input document for getting content

    Returns:
        str: The embedding vector
    """
    try:
        text = doc[feature_key]
        client = OpenAI(api_key=api_key)

        response = client.embeddings.create(input=text, model=model)
        embedding = response.data[0].embedding  # embedding vector
        return embedding
    except Exception as e:
        return []