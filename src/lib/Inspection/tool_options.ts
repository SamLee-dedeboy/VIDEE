
  export const tool_options = {
    data_transform_tool: [
        {
            "name": "Data Transformation",
            "parameters": {
                "transform_code": {
                    "type": "string",
                    "description": "Python code for data transformation"
                }
            }
        }
    ],
    embedding_tool: [
        {
            "provider": "openai",
            "Good for": "High-quality embeddings, semantic search, clustering",
            "Note": "Requires API key and internet connection",
            "parameters": {
                "model": {
                    "type": "string",
                    "description": "Model name or path"
                }
            }
        },
        {
            "provider": "sentence_transformers",
            "Good for": "Local processing without API calls, multilingual support",
            "Note": "No API key and internet connection required",
            "parameters": {
                "model": {
                    "type": "string",
                    "description": "Model name or path"
                }
            }
        },

    ],
    dim_reduction_tool: [
        {
            "algorithm": "pca",
            "Good for": "Linear dimensionality reduction, preserving global structure",
            "Note": "Fast, but may not capture non-linear relationships",
            "parameters": {
              "n_components": {
                "type": "int",
                "description": "Number of dimensions to reduce to"
              },
              "whiten": {
                "type": "boolean",
                "description": "Whether to whiten the data"
              }
            }
          },
          {
            "algorithm": "tsne",
            "Good for": "Non-linear dimensionality reduction, preserving local structure",
            "Note": "Better for visualization but computationally intensive",
            "parameters": {
              "n_components": {
                "type": "int",
                "description": "Number of dimensions to reduce to"
              },
              "perplexity": {
                "type": "float",
                "description": "Related to number of nearest neighbors (default 30)"
              },
              "early_exaggeration": {
                "type": "float",
                "description": "Control early clustering (default 12)"
              },
              "learning_rate": {
                "type": "float",
                "description": "Learning rate (default 200)"
              }
            }
          },
          {
            "algorithm": "umap",
            "Good for": "Non-linear dimensionality reduction with better global structure than t-SNE",
            "Note": "Fast and effective for visualization and machine learning",
            "parameters": {
              "n_components": {
                "type": "int",
                "description": "Number of dimensions to reduce to"
              },
              "n_neighbors": {
                "type": "int",
                "description": "Size of local neighborhood (default 15)"
              },
              "min_dist": {
                "type": "float",
                "description": "Minimum distance between points (default 0.1)"
              },
              "metric": {
                "type": "string",
                "description": "Distance metric to use (default 'euclidean')"
              }
            }
          }
    ],
    clustering_tool: [
        {
            "algorithm": "kmeans",
            "Good for": "Simple clustering with roughly equal-sized, well-separated clusters",
            "parameters": {
            "n_clusters": {
                "type": "int",
                "description": "Number of clusters to form"
            },
            "init": {
                "type": "enum",
                "description": "Method for initialization",
                "options": ["k-means++", "random"]
            },
            "n_init": {
                "type": "int",
                "description": "Number of initializations to try"
            },
            "max_iter": {
                "type": "int",
                "description": "Maximum number of iterations"
            },
            }
        },
        {
        "algorithm": "dbscan",
        "Good for": "Finding clusters of arbitrary shape, handling noise/outliers",
        "parameters": {
            "eps": {
            "type": "float",
            "description": "Maximum distance between samples for neighborhood"
            },
            "min_samples": {
            "type": "int",
            "description": "Minimum number of samples in a neighborhood"
            },
            "metric": {
            "type": "string",
            "description": "Distance metric to use"
            }
        }
        },
        {
        "algorithm": "agglomerative",
        "Good for": "Finding hierarchical relationships, generating dendrograms",
        "parameters": {
            "n_clusters": {
            "type": "int",
            "description": "Number of clusters to form"
            },
            "linkage": {
            "type": "enum",
            "description": "Linkage criterion",
            "options": ["ward", "complete", "average", "single"]
            },
            "affinity": {
            "type": "string",
            "description": "Distance metric to use"
            }
        }
        },
        {
        "algorithm": "gaussian_mixture",
        "Good for": "Soft clustering with probability distributions",
        "parameters": {
            "n_components": {
            "type": "int",
            "description": "Number of mixture components"
            },
            "covariance_type": {
            "type": "enum",
            "description": "Type of covariance",
            "options": ["full", "tied", "diag", "spherical"]
            },
            "max_iter": {
            "type": "int",
            "description": "Maximum number of iterations"
            }
        }
        },
        {
        "algorithm": "hdbscan",
        "Good for": "Finding clusters of varying densities, robust to noise",
        "parameters": {
            "min_cluster_size": {
            "type": "int",
            "description": "Minimum size for a cluster"
            },
            "min_samples": {
            "type": "int",
            "description": "Minimum number of samples in neighborhood"
            },
            "cluster_selection_epsilon": {
            "type": "float",
            "description": "Distance threshold for cluster formation"
            }
        }
        },
    ]
  }