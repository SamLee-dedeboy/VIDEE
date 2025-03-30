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
                       feature_key: str = "embeddings",
                       algorithm: str = "pca",
                       n_components: int = 50,
                       **kwargs) -> List[List[List[float]]]:
    """
    Reduces dimensionality of feature vectors in the input documents.

    Args:
        inputs: Input documents in json format, where each document contains an array of embedding vectors
        feature_key: Key in each input dictionary containing an array of embedding vectors (default: "embeddings")
        algorithm: Dimensionality reduction algorithm to use (default: "pca"), see _REDUCTION_MODELS
        n_components: Number of components in the reduced space (default: 50)
        **kwargs: Additional parameters to pass to the dimensionality reduction algorithm

    Returns:
        List of lists containing reduced embeddings for each document
    """
    '''
    input format
    inputs: [
    // each document / global state object
        {
            'embeddings': [
                [0,1, 0.03...],
                [0,1, 0.03...],
            ]
        }
    ]
    '''

    try:
        # Initialize result structure matching input structure
        result = [[] for _ in range(len(inputs))]

        # Prepare for processing
        all_embeddings = []  # Will hold all embeddings from all documents
        doc_indices = []     # Will track which document each embedding came from
        embedding_indices = []  # Will track the position of each embedding within its document

        # Extract all embeddings while tracking their origins
        for doc_idx, doc in enumerate(inputs):
            embeddings_list = doc.get(feature_key, [])
            
            # Skip if the document has no embeddings or feature_key doesn't exist
            if not embeddings_list or not isinstance(embeddings_list, list):
                continue
                
            # Process each embedding in the document
            for emb_idx, embedding in enumerate(embeddings_list):
                # Skip invalid embeddings (non-lists or empty lists)
                if not isinstance(embedding, list) or not embedding:
                    continue
                    
                # Store valid embedding and its indices
                all_embeddings.append(embedding)
                doc_indices.append(doc_idx)
                embedding_indices.append(emb_idx)

        # If no valid embeddings found, return the empty result structure
        if not all_embeddings:
            logging.warning(f"No valid embeddings found with key: {feature_key}")
            return result

        # Convert to numpy array for processing
        data_array = np.array(all_embeddings)

        # Check if algorithm exists, fallback to PCA if not
        if algorithm not in _REDUCTION_MODELS:
            logging.warning(f"Unknown dimensionality reduction algorithm: {algorithm}, falling back to pca")
            algorithm = "pca"
        kwargs['n_components'] = n_components
        model = _REDUCTION_MODELS[algorithm](**kwargs)

        try:
            # Apply dimensionality reduction
            reduced_data = model.fit_transform(data_array)
        except Exception as e:
            logging.error(f"Error in dimensionality reduction: {e}")
            return result

        # Put reduced embeddings back in their original document structure
        for i, reduced_vec in enumerate(reduced_data):
            doc_idx = doc_indices[i]
            emb_idx = embedding_indices[i]
            
            # Extend result list for this document if needed
            while len(result[doc_idx]) <= emb_idx:
                result[doc_idx].append([])
                
            # Insert the reduced vector
            result[doc_idx][emb_idx] = reduced_vec.tolist()

        return result
    except Exception as e:
        logging.error(f"Error in dim_reduction_tool: {e}")
        return [[] for _ in range(len(inputs))]