import numpy as np
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
import hdbscan
from bertopic import BERTopic
from umap import UMAP

class ClusteringModel:
    """Base class for clustering models"""
    def __init__(self, **kwargs):
        self.model = None
        self.kwargs = kwargs

    def fit_predict(self, data: np.ndarray) -> np.ndarray:
        raise NotImplementedError

class KMeansCluster(ClusteringModel):
    """
    Performs K-Means clustering to partition doc (embeddings) into k clusters.

    Some prompting Notes for planning
    - we need the execution plan to give the number of clusters in advance
    - could be used with document categorization with known categories

    Expected input:
    - list of docs represented by embeddings vectors

    Output labels
    """
    def fit_predict(self, data: np.ndarray) -> np.ndarray:
        n_clusters = min(self.kwargs.get('n_clusters', 3), len(data))
        self.model = KMeans(
            n_clusters=n_clusters,
            random_state=self.kwargs.get('random_state', 42),
            n_init=self.kwargs.get('n_init', 10)
        )

        return self.model.fit_predict(data)

class DBSCANCluster(ClusteringModel):
    """
    Performs DBSCAN to group docs (embeddings) based on density.

    Some prompting Notes for planning
    - Suitable for discovering clusters of arbitrary shape.
    - the plan does not need to specify the number of clusters in advance.

    Expected input:
    - list of docs represented by embeddings vectors

    Output labels
    """
    def fit_predict(self, data: np.ndarray) -> np.ndarray:
        self.model = DBSCAN(
            eps=self.kwargs.get('eps', 0.5),
            min_samples=self.kwargs.get('min_samples', 3)
        )
        return self.model.fit_predict(data)

class AgglomerativeCluster(ClusteringModel):
    """
    Performs hierarchical clustering using Agglomerative Clustering, which can be used for topic modeling.

    Some prompting Notes for planning
    - this is suitable for creating hierarchical relationships between documents.
    - Useful when cluster structure is important.
    - Works well with documents that have nested categories.

    Expected input:
    - list of docs represented by embeddings vectors

    Output labels
    """
    def fit_predict(self, data: np.ndarray) -> np.ndarray:
        n_clusters = min(self.kwargs.get('n_clusters', 3), len(data))
        self.model = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage=self.kwargs.get('linkage', 'ward')
        )
        return self.model.fit_predict(data)

class GaussianMixtureCluster(ClusteringModel):
    """
    Performs clustering using GMM

    Some prompting Notes for planning
    - Suitable when clusters may overlap.

    Expected input:
    - list of docs represented by embeddings vectors

    Output labels
    """
    def fit_predict(self, data: np.ndarray) -> np.ndarray:
        n_components = min(self.kwargs.get('n_components', 3), len(data))
        self.model = GaussianMixture(
            n_components=n_components,
            random_state=self.kwargs.get('random_state', 42)
        )
        self.model.fit(data)
        return self.model.predict(data)

class HDBSCANCluster(ClusteringModel):
    """
    Performs HDBSCAN that can handle clusters of varying densities.

    Some prompting Notes for planning
    - Suitable for detecting clusters of different densities and shapes.
    - Does not require specifying the number of clusters in advance.
    - this handles high-dimensional data better than DBSCAN.

    Expected input:
    - list of docs represented by embeddings vectors

    Output labels
    """

    def fit_predict(self, data: np.ndarray) -> np.ndarray:
        self.model = hdbscan.HDBSCAN(
            min_cluster_size=self.kwargs.get('min_cluster_size', 3),
            min_samples=self.kwargs.get('min_samples', None),
            alpha=self.kwargs.get('alpha', 1.0),
            cluster_selection_epsilon=self.kwargs.get('cluster_selection_epsilon', 0.0),
            metric=self.kwargs.get('metric', 'euclidean'),
            prediction_data=True
        )
        return self.model.fit_predict(data)

class BERTopicCluster(ClusteringModel):
    """
    Topic modeling using BERT embeddings, UMAP dimension reduction, and HDBSCAN clustering.

    Some prompting Notes for planning
    - Clusters text documents based on semantic meaning.
    - Provides dynamic topic representation without requiring a predefined number of topics.
    - Useful for discovering latent topics in large text collections.

    Expected input:
    - Text documents (processed to embeddings internally)
    - Can also accept pre-computed embeddings

    Output labels
    """
    def fit_predict(self, data: np.ndarray) -> np.ndarray:
        # For BERTopic, we need original text if available
        original_docs = self.kwargs.get('original_docs', [])

        # BERTopic parameters
        min_topic_size = self.kwargs.get('min_topic_size', 2)
        nr_topics = self.kwargs.get('nr_topics', 'auto')

        # BERTopic needs enough samples for UMAP and HDBSCAN to work properly..
        if len(data) < 5:
            logging.warning("Dataset too small for BERTopic. Using fallback clustering.")
            # Fallback to a simpler clustering algorithm for very small datasets
            fallback = KMeansCluster(n_clusters=min(2, len(data)))
            return fallback.fit_predict(data)

        try:
            # Initialize the model with customized UMAP parameters for small datasets
            from umap import UMAP
            from hdbscan import HDBSCAN
            umap_model = UMAP(
                n_neighbors=min(3, len(data)-1),
                n_components=min(2, len(data)-1),
                min_dist=0.0,
                metric='cosine'
            )

            # Create HDBSCAN model with appropriate parameters
            hdbscan_model = HDBSCAN(
                min_cluster_size=min(2, len(data)),
                min_samples=1,
                prediction_data=True
            )

            self.model = BERTopic(
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                min_topic_size=min(min_topic_size, len(data)),
                nr_topics=nr_topics,
                calculate_probabilities=True
            )
            if original_docs is not None:
                topics, _ = self.model.fit_transform(original_docs, embeddings=data)
                return np.array(topics)
            topics, _ = self.model.fit_transform([""] * len(data), embeddings=data)
            return np.array(topics)

        except Exception as e:
            logging.error(f"BERTopic error: {e}")
            # Fallback to a simpler clustering algorithm!
            logging.warning("Falling back to KMeans clustering due to BERTopic error")
            fallback = KMeansCluster(n_clusters=min(2, len(data)))
            return fallback.fit_predict(data)

# Registry of available clustering algorithms
_CLUSTERING_MODELS = {
    'kmeans': KMeansCluster,
    'dbscan': DBSCANCluster,
    'agglomerative': AgglomerativeCluster,
    'gaussian_mixture': GaussianMixtureCluster,
    'hdbscan': HDBSCANCluster,
    'bertopic': BERTopicCluster
}

def register_clustering_model(name: str, model_class: type):
    """Register a new clustering model"""
    _CLUSTERING_MODELS[name] = model_class

def evaluate_clustering(data: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    """
    Evaluate clustering quality with metrics, I _think_ this could be helpful for our evaluator

    Args:
        data: Feature vectors used for clustering
        labels: Cluster assignments from the clustering algorithm

    Returns:
        Dictionary of metric names and values
    """
    metrics = {}
    unique_labels = set(labels)
    if len(unique_labels) > 1 and -1 not in unique_labels:
        try:
            metrics['silhouette_score'] = silhouette_score(data, labels)
        except Exception as e:
            logging.warning(f"Error calculating silhouette score: {e}")

    # Add more metrics if needed

    return metrics

def clustering_tool(inputs: List[Dict[str, Any]],
                   n_clusters: int = 3,
                   feature_key: str = "embedding",
                   algorithm: str = "kmeans",
                   return_metrics: bool = False,
                   **kwargs) -> Union[List[int], Dict[str, Any]]:
    """
    Performs clustering on feature vectors extracted from inputs.

    Args:
        inputs: Input documents in json format
        n_clusters: Number of clusters (default: 3)
        feature_key: Key in each input doc containing the feature vector (default: "embedding")
        algorithm: Clustering algorithm to use (default: "kmeans")
                   Options: kmeans, dbscan, agglomerative, gaussian_mixture, hdbscan, bertopic
        return_metrics: Whether to return evaluation metrics (default: False)
        **kwargs: Additional parameters to pass to the clustering algorithm
                  For BERTopic: `content` can be passed to provide text documents

    Returns:
        List of cluster labels or dictionary with results and metrics
    """
    try:
        # Extract feature vectors from inputs
        # data = [i.get(feature_key, []) for i in inputs]
        data = inputs

        # For BERTopic, we might need original texts
        if algorithm == 'bertopic':
            # original doc content
            feature_key = kwargs.get('feature_key', 'content')
            if feature_key in inputs[0]:
                kwargs['original_docs'] = [i.get(feature_key, "") for i in inputs]

        # Filter out empty vectors
        valid_indices = [i for i, vec in enumerate(data) if vec]
        valid_data = [data[i] for i in valid_indices]

        # there's no valid embedding, generate it!
        if (len(valid_data) == 0
                or not (isinstance(valid_data[0], list) and len(valid_data[0]) > 0)
                or not isinstance(valid_data[0][0], (int, float))
        ):
            # original doc content
            feature_key = kwargs.get('feature_key', 'content')
            if feature_key in inputs[0]:
                kwargs['original_docs'] = [i.get(feature_key, "") for i in inputs]
            else:
                kwargs['original_docs'] = [str(obj) for obj in inputs]
            from sentence_transformers import SentenceTransformer
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            valid_data = [embedding_model.encode(doc) for doc in kwargs['original_docs']]
            valid_indices = [i for i in range(len(valid_data))]

        if not valid_data:
            logging.warning(f"No valid feature vectors found with key: {feature_key}")
            return [0] * len(inputs)  # Default to cluster 0

        data_array = np.array(valid_data)

        # Check if algorithm exists, if not let's default to kmeans..
        if algorithm not in _CLUSTERING_MODELS:
            logging.warning(f"Unknown clustering algorithm: {algorithm}, falling back to kmeans")
            algorithm = "kmeans"

        # Create clustering model
        kwargs['n_clusters'] = n_clusters
        model = _CLUSTERING_MODELS[algorithm](**kwargs)

        # Perform clustering
        valid_labels = model.fit_predict(data_array)

        # Create result array with same length as inputs
        result = [0] * len(inputs)  # Default to cluster 0
        for idx, valid_idx in enumerate(valid_indices):
            result[valid_idx] = int(valid_labels[idx])

        # If only labels are requested
        if not return_metrics:
            return result

        # Build extended result if requested, for example, evaluation metrics..
        output = {'labels': result}

        if return_metrics:
            output['metrics'] = evaluate_clustering(data_array, valid_labels)

        return output
    except Exception as e:
        logging.error(f"Error in clustering_tool: {e}")
        return [0] * len(inputs)  # Default to cluster 0