# cluster_server.py
from mcp.server.fastmcp import FastMCP
import numpy as np
from sklearn.cluster import KMeans

mcp = FastMCP("Clustering")

@mcp.tool()
def cluster_points(points, n_clusters=3):
    """
    Cluster a list of 2D points using KMeans.

    Parameters:
        points (list of lists or array-like): A list where each element represents a point as [x, y].
        n_clusters (int): The number of clusters to form.

    Returns:
        numpy.ndarray: Array containing the cluster label for each point.
    """
    # Convert the list of points into a NumPy array
    data = np.array(points)

    # Instantiate and fit the KMeans model
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(data)

    return kmeans.labels_


if __name__ == "__main__":
    mcp.run()
    # cluster(None)