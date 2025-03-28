import numpy as np
from typing import List, Dict, Any, Optional, Union
import logging
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import io
import base64
import umap

class DimensionalityReductionModel:
    """Base class for dimensionality reduction models"""
    def __init__(self, **kwargs):
        self.model = None
        self.kwargs = kwargs

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        raise NotImplementedError

class PCAModel(DimensionalityReductionModel):
    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        n_components = min(self.kwargs.get('n_components', 50), data.shape[1], data.shape[0])
        self.model = PCA(n_components=n_components)
        return self.model.fit_transform(data)

class TSNEModel(DimensionalityReductionModel):
    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        n_components = min(self.kwargs.get('n_components', 50), data.shape[1], data.shape[0])
        # we need to tune this, probably ask llm to give the parameter?
        perplexity = min(self.kwargs.get('perplexity', 10), data.shape[0] - 1)

        self.model = TSNE(
            n_components=n_components,
            perplexity=perplexity,
            random_state=self.kwargs.get('random_state', 42)
        )
        return self.model.fit_transform(data)

class UMAPModel(DimensionalityReductionModel):
    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        n_components = min(self.kwargs.get('n_components', 50), data.shape[1], data.shape[0])
        n_neighbors = min(self.kwargs.get('n_neighbors', 10), data.shape[0] - 1)

        self.model = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=self.kwargs.get('min_dist', 0.1),
            random_state=self.kwargs.get('random_state', 42)
        )
        return self.model.fit_transform(data)

# Registry of available dimensionality reduction models
_REDUCTION_MODELS = {
    'pca': PCAModel,
    'tsne': TSNEModel,
    'umap': UMAPModel
}

def register_reduction_model(name: str, model_class: type):
    """Register a new dimensionality reduction model"""
    _REDUCTION_MODELS[name] = model_class

def dim_reduction_tool(inputs: List[Dict[str, Any]],
                       feature_key: str = "embedding",
                       algorithm: str = "pca",
                       n_components: int = 50,
                       **kwargs) -> List[List]:
    """
    Reduces dimensionality of feature vectors in the input documents.

    Args:
        inputs: Input documents in json format
        feature_key: Key in each input dictionary containing the feature vector (default: "embedding")
        algorithm: Dimensionality reduction algorithm to use (default: "pca"), see _REDUCTION_MODELS
        n_components: Number of components in the reduced space (default: 50)
        **kwargs: Additional parameters to pass to the dimensionality reduction algorithm

    Returns:
        List of documents with reduced features added
    """
    try:
        for i in inputs:
            if isinstance(i.get(feature_key, ''), str):
                i[feature_key] = i[feature_key].split()
        # Extract feature vectors from inputs
        data = [i.get(feature_key, []) for i in inputs]
        result = [[]] * len(inputs)

        # Filter out empty vectors
        valid_indices = [i for i, vec in enumerate(data) if vec]
        valid_data = [data[i] for i in valid_indices]

        if not valid_data:
            logging.warning(f"No valid feature vectors found with key: {feature_key}")
            return result

        data_array = np.array(valid_data)

        if algorithm not in _REDUCTION_MODELS:
            logging.warning(f"Unknown dimensionality reduction algorithm: {algorithm}, falling back to pca")
            algorithm = "pca"
        kwargs['n_components'] = n_components
        model = _REDUCTION_MODELS[algorithm](**kwargs)

        try:
            reduced_data = model.fit_transform(data_array)
        except Exception as e:
            logging.error(f"Error in dimensionality reduction: {e}")
            return result

        # Add back reduced features to valid documents
        for idx, reduced_vec in zip(valid_indices, reduced_data):
            result[idx] = reduced_vec.tolist()

        return result
    except Exception as e:
        logging.error(f"Error in dim_reduction_tool: {e}")
        return [[]] * len(inputs)