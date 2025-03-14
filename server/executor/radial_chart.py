import concurrent
from tqdm import tqdm
import tiktoken
import numpy as np
from sklearn.cluster import AgglomerativeClustering, OPTICS, KMeans
from sklearn.metrics.pairwise import cosine_distances
from scipy.optimize import minimize
from collections import defaultdict
from openai import RateLimitError, APITimeoutError
from openai import OpenAI
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
import json
import time
import statistics
import random
import asyncio
import traceback
from tqdm.asyncio import tqdm_asyncio
from sklearn.feature_extraction.text import TfidfVectorizer
from server.utils import extract_json_content


async def radial_dr(texts: list[str], model: str, api_key: str):
    print("generating embeddings...")
    # embeddings = await multithread_embeddings(texts, api_key)
    embeddings = tf_idf_embeddings(texts)
    # clusters = cluster.optics(embeddings)
    print("generating clusters...")
    clusters = cluster(embeddings)
    # topic labels, dict: cluster label -> topic
    print("generating clusters topics...")
    cluster_topics = await cluster_topic_assignments(clusters, texts, model, api_key)

    # print("calculating dr...")
    # all_angles = circular_dr(embeddings)
    # cluster_angles = defaultdict(list)
    # for cluster_label, angle in zip(clusters, all_angles):
    #     cluster_angles[cluster_label].append(angle)
    # cluster_mean_angles = [
    #     (cluster_label, statistics.mean(angles))
    #     for cluster_label, angles in cluster_angles.items()
    # ]
    # cluster_orders = sorted(cluster_mean_angles, key=lambda x: x[1])
    # # create a dict such that the key is the cluster label and the value is the index in the cluster_orders
    # cluster_orders = {
    #     cluster_label: i for i, (cluster_label, _) in enumerate(cluster_orders)
    # }
    clusters, cluster_orders, all_angles = divide_by_cluster_size(clusters)

    return clusters, cluster_orders, cluster_topics, all_angles
    # for i, datum in enumerate(data):
    #     data[i]["cluster"] = cluster_orders[clusters[i]]
    #     data[i]["cluster_label"] = cluster_topics[clusters[i]]
    #     data[i]["angle"] = all_angles[i]

    return json.dumps(data, default=vars)


def divide_by_cluster_size(clusters: list[str]):
    cluster_sizes = defaultdict(int)
    for cluster in clusters:
        cluster_sizes[cluster] += 1
    cluster_orders = list(cluster_sizes.keys())
    total_nodes = len(clusters)
    cluster_angles = [
        cluster_sizes[cluster] / total_nodes for cluster in cluster_orders
    ]
    cluster_ranges = []
    for i, cluster in enumerate(cluster_orders):
        start = sum(cluster_angles[:i])
        end = sum(cluster_angles[: i + 1])
        cluster_ranges.append((start, end))
    all_angles = []
    for cluster_label in clusters:
        start, end = cluster_ranges[cluster_orders.index(cluster_label)]
        angle = random.uniform(start, end) * 2 * np.pi
        all_angles.append(angle)

    return clusters, cluster_orders, all_angles


def tf_idf_embeddings(texts):
    vectorizer = TfidfVectorizer(max_features=1000)
    tfidf_matrix = vectorizer.fit_transform(texts)
    return tfidf_matrix.toarray()


async def call_agent(agent, user_message):
    enc = tiktoken.encoding_for_model("gpt-4o-mini")
    token_length = len(enc.encode(user_message))
    print("calling agent - token length: ", token_length)
    response = await agent.on_messages(
        [TextMessage(content=user_message, source="user")],
        cancellation_token=CancellationToken(),
    )
    return response


async def parallel_call_agents(agent, user_messages):
    tasks = [call_agent(agent, user_message) for user_message in user_messages]
    # results = await asyncio.gather(*tasks)
    results = await tqdm_asyncio.gather(*tasks, desc="generating topics")
    return results


async def multithread_embeddings(texts, api_key):
    tasks = [get_embedding(text, api_key) for text in texts]
    # results = await asyncio.gather(*tasks)  # Runs network requests concurrently
    results = await tqdm_asyncio.gather(*tasks, desc="generating embeddings")
    return results


async def get_embedding(text, api_key, model="text-embedding-3-small"):
    return await asyncio.to_thread(_get_embedding_block, text, api_key, model)


def _get_embedding_block(text, api_key, model="text-embedding-3-small"):
    client = OpenAI(api_key=api_key)
    enc = tiktoken.encoding_for_model(model)
    # print("tokens: ", len(enc.encode(text)), len(enc.encode(text)) > 8191)
    while len(enc.encode(text)) > 8191:
        text = text[:-100]
        print("truncated: ", len(enc.encode(text)))
    try:
        return client.embeddings.create(input=text, model=model).data[0].embedding
    except Exception as e:
        print(traceback.format_exc())
        # return get_embedding(text, api_key, model)


def cluster(X):
    if len(X) == 1:
        return [1]
    X = np.array(X)
    # clustering = AgglomerativeClustering(
    #     n_clusters=10,
    #     # distance_threshold=0.5,
    #     metric="cosine",
    #     linkage="average",
    # ).fit(X)
    clustering = KMeans(n_clusters=min(10, len(X)), random_state=0, n_init="auto").fit(
        X
    )
    return list(map(lambda label: int(label), clustering.labels_))


async def cluster_topic_assignments(clusters, texts, model, api_key):
    cluster_texts = defaultdict(list)
    for cluster, text in zip(clusters, texts):
        cluster_texts[cluster].append(text)
    cluster_list = []
    topic_assignment_agent = generate_topic_assignment_agent(model, api_key)
    user_messages = []
    for cluster, texts in cluster_texts.items():
        enc = tiktoken.encoding_for_model(model)
        token_length = len(enc.encode("\n".join(texts)))
        # print(cluster, "token length: ", token_length)
        # while token_length > 70000:  # 128000 is the max token limit for GPT-4o-mini
        #     texts = random.sample(texts, len(texts) // 2)
        #     token_length = len(enc.encode("\n".join(texts)))
        texts = random.sample(texts, min(len(texts), 25))
        token_length = len(enc.encode("\n".join(texts)))
        # print(cluster, "token length: ", token_length)
        user_messages.append("\n".join(texts))
        cluster_list.append(cluster)
    responses = await parallel_call_agents(topic_assignment_agent, user_messages)
    # for response in responses:
    # print(response.chat_message.content)
    # print("============================")
    responses = [response.chat_message.content for response in responses]
    # responses = [
    #     extract_json_content(response.chat_message.content)["topic"]
    #     for response in responses
    # ]
    # responses = [
    #     json.loads(response.chat_message.content)["topic"] for response in responses
    # ]
    cluster_topics = {
        cluster: response for cluster, response in zip(cluster_list, responses)
    }
    return cluster_topics


def generate_topic_assignment_agent(model: str, api_key: str):
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        temperature=0.0,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": False,
        },
    )
    agent = AssistantAgent(
        name="goal_decomposition_agent",
        model_client=model_client,
        system_message="""You are a topic assignment system. The user will provide you with a bunch of texts. You need to assign one topic to summarize all of them. 
            The topic should be a simple noun-phrase. Only one topic should be generated.
            Reply with a single noun-phrase as the topic.
            """,
    )
    return agent


def circular_dr(X):
    D = cosine_distances(X)
    angles = optimize_positions(D)
    return angles


def optimize_positions(D, initial_theta=None, verbose=False):
    """
    Optimize the positions of points on a circle to preserve the distances in D.

    Parameters:
    - D: n x n distance matrix.
    - initial_theta: Optional initial guess for the angles.
    - verbose: If True, print optimization details.

    Returns:
    - Optimized angles theta (in radians).
    """
    n = D.shape[0]

    d_min = np.min(D)
    d_max = np.max(D)
    D = (D - d_min) / (d_max - d_min)
    if initial_theta is None:
        # Initialize theta randomly between 0 and 2pi
        initial_theta = np.random.uniform(0, 2 * np.pi, n)

    # Define bounds for each theta: [0, 2pi]
    bounds = [(0, 2 * np.pi) for _ in range(n)]

    # Optionally, fix the first angle to 0 to remove rotational symmetry
    # Uncomment the following lines if you want to fix theta_0 = 0
    # bounds = [(0, 0)] + [(0, 2 * np.pi) for _ in range(n - 1)]

    # Define the objective function with D fixed
    obj = lambda theta: objective(theta, D)

    # Perform the optimization
    result = minimize(
        obj,
        initial_theta,
        method="L-BFGS-B",
        bounds=bounds,
        options={"disp": verbose, "maxfun": 9999999},
    )

    if not result.success:
        raise ValueError("Optimization failed: " + result.message)

    optimized_theta = result.x
    return optimized_theta


def objective(theta, D):
    """
    Objective function to minimize: sum of squared differences between
    circular distances and the given distance matrix D.

    Parameters:
    - theta: array of angles (in radians) for each point.
    - D: n x n distance matrix.

    Returns:
    - Sum of squared differences.
    """
    n = len(theta)
    # Compute pairwise circular distances
    d = 1 - np.cos(
        np.minimum(
            np.abs(theta[:, np.newaxis] - theta[np.newaxis, :]),
            2 * np.pi - np.abs(theta[:, np.newaxis] - theta[np.newaxis, :]),
        )
    )

    # Compute the difference only for i < j to avoid double counting and zero diagonals
    mask = np.triu(np.ones((n, n)), k=1).astype(bool)
    diff = d[mask] - 2 * D[mask]

    return np.sum(diff**2)
