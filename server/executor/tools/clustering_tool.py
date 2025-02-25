import numpy as np
from sklearn.cluster import KMeans
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool

def clustering_tool(inputs: list[dict], n_clusters: int = 3, feature_key: str = "embedding"):
    """
    Creates a runnable that performs KMeans clustering on feature vectors extracted from inputs.

    Args:
        inputs: input documents in json format
        n_clusters (int): Number of clusters for KMeans (default: 3).
        feature_key (str): Key in each input dictionary containing the feature vector (default: "features").

    Returns:
        List of clustering results labels
    """
    # Extract feature vectors from inputs
    data = [i[feature_key] for i in inputs]
    data_array = np.array(data)
    # Perform KMeans clustering, we can choose other algorithms later
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(data_array)
    return kmeans.labels_.tolist()