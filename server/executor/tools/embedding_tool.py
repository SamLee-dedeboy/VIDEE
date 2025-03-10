from openai import OpenAI
import numpy as np
from typing import List, Dict, Union, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential


class EmbeddingProvider:
    """Base class for embeddingProviders"""

    def get_embedding(self, text: str, model: str) -> List[float]:
        raise NotImplementedError

    def get_batch_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        return [self.get_embedding(text, model) for text in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def get_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        try:
            response = self.client.embeddings.create(input=text, model=model)
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Error generating embedding with OpenAI: {e}")
            # don't raise exception for now
            # raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def get_batch_embeddings(self, texts: List[str], model: str = "text-embedding-ada-002") -> List[List[float]]:
        try:
            response = self.client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in response.data]
        except Exception as e:
            logging.error(f"Error generating batch embeddings with OpenAI: {e}")
            # don't raise exception for now
            # raise


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name_or_path: Optional[str] = None):
        """
        SentenceTransformers embedding provider, https://sbert.net/

        Args:
            model_name_or_path: Model name or path to load. If None, using the default model all-MiniLM-L6-v2
        """
        from sentence_transformers import SentenceTransformer
        if model_name_or_path is None:
            model_name_or_path = 'all-MiniLM-L6-v2'
        self.model = SentenceTransformer(model_name_or_path)

    def get_embedding(self, text: str, model: str = None) -> List[float]:
        """
        Generate embedding for given text.

        Args:
            text: The input text to embed
            model: This param is just for Class compatibility. Model should be provided during initialization.

        Returns:
            embedding
        """
        try:
            # Generate embedding and convert to list
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logging.error(f"Error generating embedding with SentenceTransformers: {e}")
            return []

    def get_batch_embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts to embed
            model: Same as above function, this param is just for Class compatibility. Model should be provided during initialization.

        Returns:
            A list of embedding vectors for the given list of texts
        """
        try:
            # Batch encode all texts at once (more efficient)
            embeddings = self.model.encode(texts)
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logging.error(f"Error generating batch embeddings with SentenceTransformers: {e}")
            return [[] for _ in texts]


# Singleton registry of providers
_PROVIDERS = {
    "openai": OpenAIEmbeddingProvider,
    "sentence_transformers": SentenceTransformersEmbeddingProvider  # Add the new provider
}


def register_embedding_provider(name: str, provider_class: type):
    """Register a new embedding provider"""
    _PROVIDERS[name] = provider_class


def embedding_tool(doc: Dict[str, Any], api_key: str = None, model: str = "text-embedding-ada-002",
                   feature_key: str = "content", provider: str = "openai") -> List[float]:
    """
    Generates an embedding for the given text using the specified embedding provider.

    Args:
        doc: dictionary as single input documents
        feature_key: Key in the input document for getting content, for example, 'content'
        api_key: API key for the embedding provider
        model: The embedding model to use
        provider: Name of the embedding provider, see `_PROVIDERS`.

    Returns:
        List[float]: The embedding vector or empty list on error
    """
    try:
        text = doc[feature_key]
        if not text or not isinstance(text, str):
            logging.warning(f"Invalid text in document for key {feature_key}, force to use the input object for embedding")
            # original doc content
            text = str(doc)

        if provider not in _PROVIDERS:
            logging.error(f"Unknown embedding provider: {provider}")
            return []

        # Initialize provider with api_key, model if needed
        if provider == "openai":
            provider_instance = _PROVIDERS[provider](api_key)
        elif provider == "sentence_transformers":
            provider_instance = _PROVIDERS[provider](model_name_or_path=model)
        else:
            provider_instance = _PROVIDERS[provider](api_key)

        return provider_instance.get_embedding(text, model)
    except Exception as e:
        logging.error(f"Error in embedding_tool: {e}")
        return []


def batch_embedding_tool(docs: List[Dict[str, Any]], api_key: str = None, model: str = "text-embedding-ada-002",
                         feature_key: str = "content", provider: str = "openai") -> List[List[float]]:
    """
    Generates embeddings for multiple docs in batch.

    Args:
        docs: List of document dictionaries for embedding
        feature_key: Key in each input document for getting content
        api_key: API key for the embedding provider
        model: The embedding model to use
        provider: Name of the embedding provider

    Returns:
        List[List[float]]: List of embedding vectors
    """
    try:
        texts = [doc.get(feature_key, "") for doc in docs]
        texts = [t for t in texts if t and isinstance(t, str)]

        if not texts:
            logging.warning(
                f"Invalid text in document for key {feature_key}, force to use the input object for embedding")
            # original doc content
            texts = [str(doc) for doc in docs]

        if provider not in _PROVIDERS:
            logging.error(f"Unknown embedding provider: {provider}")
            return [[] for _ in docs]

        # Initialize provider with api_key, model if needed
        if provider == "openai":
            provider_instance = _PROVIDERS[provider](api_key)
        elif provider == "sentence_transformers":
            provider_instance = _PROVIDERS[provider](model_name_or_path=model)
        else:
            provider_instance = _PROVIDERS[provider](api_key)

        embeddings = provider_instance.get_batch_embeddings(texts, model)

        # Align results with input docs
        result = []
        embedding_idx = 0
        for doc in docs:
            if feature_key in doc and doc[feature_key] and isinstance(doc[feature_key], str):
                result.append(embeddings[embedding_idx])
                embedding_idx += 1
            else:
                result.append([])

        return result
    except Exception as e:
        logging.error(f"Error in batch_embedding_tool: {e}")
        return [[] for _ in docs]