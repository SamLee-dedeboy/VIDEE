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
                   **kwargs) -> List[List[int]]:
    """
    Performs clustering on feature vectors extracted from inputs.

    Args:
        inputs: Input documents in json format, where each document may contain arrays of embeddings or text
        n_clusters: Number of clusters (default: 3)
        feature_key: Key in each input doc containing the feature vector or text (default: "embedding")
        algorithm: Clustering algorithm to use (default: "kmeans")
                   Options: kmeans, dbscan, agglomerative, gaussian_mixture, hdbscan, bertopic
        return_metrics: Whether to return evaluation metrics (default: False)
        **kwargs: Additional parameters to pass to the clustering algorithm

    Returns:
        List of lists containing cluster labels for each document's elements
    """
    '''
    possible input format
    // this means do clustering for each str inside each document's embedding
    inputs: [
    // each document / global state object
        {
            'embeddings': [
                [0,1, 0.03...],
                [0,1, 0.03...],
            ]
        }
    ]
    // this means do clustering for each str inside each document, need to use bertopic 
    inputs: [
        {
            'content': "str"
        }
    ]
    // this means do clustering for each str inside each document's feature key, using bertopic
    inputs: [
        {
            'summary': [
                'str1',
                'str2',
            ]
        }
    ]
    '''
    # Initialize result structure matching input structure
    result = [[] for _ in range(len(inputs))]

    if not inputs or len(inputs) == 0:
        return result
    try:
        # Prepare for processing
        all_elements = []          # Will hold all elements to cluster
        doc_indices = []           # Will track which document each element came from
        embedding_indices = []     # Will track the position of each element within its document
        is_text_data = False       # Flag to determine if we're processing text data
        original_texts = []        # Will hold original text data if processing strings

        # Process each document
        for doc_idx, doc in enumerate(inputs):
            if feature_key not in doc:
                continue

            content = doc[feature_key]

            if isinstance(content, list) and content:
                # Case 1: If content is an array of numeric arrays (embeddings)
                if all(isinstance(item, list) for item in content) and all(item and all(isinstance(x, (int, float)) for x in item) for item in content if item):
                    for emb_idx, embedding in enumerate(content):
                        if not embedding:
                            continue
                        all_elements.append(embedding)
                        doc_indices.append(doc_idx)
                        embedding_indices.append(emb_idx)
                # Case 2: If content is an array of strings
                elif all(isinstance(item, str) for item in content if item):
                    is_text_data = True
                    algorithm = 'bertopic'  # Force BERTopic for text data
                    for str_idx, text_item in enumerate(content):
                        if not text_item:
                            continue
                        original_texts.append(text_item)
                        doc_indices.append(doc_idx)
                        embedding_indices.append(str_idx)

            # Case 3: If content is a single string
            elif isinstance(content, str) and content:
                is_text_data = True
                algorithm = 'bertopic'  # Force BERTopic for text data
                original_texts.append(content)
                doc_indices.append(doc_idx)
                embedding_indices.append(0)  # Single item at position 0

            # Case 4: If content is a dict with a single key containing a list
            elif isinstance(content, dict) and len(content) == 1:
                single_value = list(content.values())[0]
                if isinstance(single_value, list):
                    if all(isinstance(item, list) and all(isinstance(x, (int, float)) for x in item) for item in single_value if item):
                        # Numeric embeddings in dict
                        for emb_idx, embedding in enumerate(single_value):
                            if not embedding:
                                continue
                            all_elements.append(embedding)
                            doc_indices.append(doc_idx)
                            embedding_indices.append(emb_idx)
                    elif all(isinstance(item, str) for item in single_value if item):
                        # String items in dict
                        is_text_data = True
                        algorithm = 'bertopic'
                        for str_idx, text_item in enumerate(single_value):
                            if not text_item:
                                continue
                            original_texts.append(text_item)
                            doc_indices.append(doc_idx)
                            embedding_indices.append(str_idx)
                else:
                    # Single non-list value in dict
                    if isinstance(single_value, str) and single_value:
                        is_text_data = True
                        algorithm = 'bertopic'
                        original_texts.append(single_value)
                        doc_indices.append(doc_idx)
                        embedding_indices.append(0)

        # Convert text data to embeddings if necessary
        if is_text_data:
            if not original_texts:
                logging.warning(f"No valid text data found with key: {feature_key}")
                return result

            # Generate embeddings for text data
            from sentence_transformers import SentenceTransformer
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            all_elements = [embedding_model.encode(text) for text in original_texts]
            kwargs['original_docs'] = original_texts

        # If no valid data found at all, return empty result
        if not all_elements:
            logging.warning(f"No valid data found with key: {feature_key}")
            return result

        # Convert to numpy array for processing
        data_array = np.array(all_elements)

        # Check if algorithm exists, fallback to appropriate default
        if algorithm not in _CLUSTERING_MODELS:
            if is_text_data:
                logging.warning(f"Unknown algorithm: {algorithm} for text data, falling back to bertopic")
                algorithm = "bertopic"
            else:
                logging.warning(f"Unknown algorithm: {algorithm}, falling back to kmeans")
                algorithm = "kmeans"

        # Configure clustering model
        kwargs['n_clusters'] = n_clusters
        model = _CLUSTERING_MODELS[algorithm](**kwargs)

        try:
            # Perform clustering
            cluster_labels = model.fit_predict(data_array)

            # Put cluster labels back in their original document structure
            for i, label in enumerate(cluster_labels):
                doc_idx = doc_indices[i]
                emb_idx = embedding_indices[i]

                # Extend result list for this document if needed
                while len(result[doc_idx]) <= emb_idx:
                    result[doc_idx].append(0)  # Default to cluster 0

                # Insert the cluster label
                result[doc_idx][emb_idx] = int(label)

            if not return_metrics:
                return result

            # Build extended result with metrics if requested
            metrics = evaluate_clustering(data_array, cluster_labels)

            # Format results with metrics
            output = []
            for doc_idx, labels in enumerate(result):
                doc_result = {
                    'labels': labels,
                    'metrics': metrics
                }
                output.append(doc_result)

            return output

        except Exception as e:
            logging.error(f"Error in clustering model: {e}")
            return result

    except Exception as e:
        logging.error(f"Error in clustering_tool: {e}")
        return [[] for _ in range(len(inputs))]