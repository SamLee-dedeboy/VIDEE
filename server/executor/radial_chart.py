import concurrent
from tqdm import tqdm
import tiktoken
import numpy as np
from sklearn.cluster import AgglomerativeClustering, OPTICS
from sklearn.metrics.pairwise import cosine_distances
from scipy.optimize import minimize
from collections import defaultdict
from openai import RateLimitError, APITimeoutError
import json
import time
import statistics


def radial_dr(texts: list[str], openai_client):
    embeddings = multithread_embeddings(openai_client, texts)
    # clusters = cluster.optics(embeddings)
    clusters = cluster(embeddings)
    # topic labels, dict: cluster label -> topic
    cluster_topics = cluster_topic_assignments(openai_client, clusters, texts)

    all_angles = circular_dr(embeddings)
    cluster_angles = defaultdict(list)
    for cluster_label, angle in zip(clusters, all_angles):
        cluster_angles[cluster_label].append(angle)
    cluster_mean_angles = [
        (cluster_label, statistics.mean(angles))
        for cluster_label, angles in cluster_angles.items()
    ]
    cluster_orders = sorted(cluster_mean_angles, key=lambda x: x[1])
    # create a dict such that the key is the cluster label and the value is the index in the cluster_orders
    cluster_orders = {
        cluster_label: i for i, (cluster_label, _) in enumerate(cluster_orders)
    }
    return clusters, cluster_orders, cluster_topics, all_angles
    # for i, datum in enumerate(data):
    #     data[i]["cluster"] = cluster_orders[clusters[i]]
    #     data[i]["cluster_label"] = cluster_topics[clusters[i]]
    #     data[i]["angle"] = all_angles[i]

    return json.dumps(data, default=vars)


def request_gpt(
    client, messages, model="gpt-4o-mini", temperature=0.5, format=None, seed=None
):
    with open("request_log.txt", "a", encoding="utf-8") as f:
        f.write(f"model: {model}, temperature: {temperature}, format: {format}\n")
        f.write(json.dumps(messages, ensure_ascii=False) + "\n")
        f.write("=====================================\n")
    try:
        if format == "json":
            response = (
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    seed=seed,
                ),
            )

        else:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, seed=seed
            )
        return response[0].choices[0].message.content
    except RateLimitError as e:
        print("RateLimitError")
        print(e)
        time.sleep(5)
        return request_gpt(client, messages, model, temperature, format)
    except APITimeoutError as e:
        print("APITimeoutError")
        print(messages)
        time.sleep(5)
        return request_gpt(client, messages, model, temperature, format)


def multithread_prompts(
    client,
    prompts,
    model="gpt-4o-mini",
    temperature=0.5,
    response_format=None,
    seed=None,
):
    l = len(prompts)
    # results = np.zeros(l)
    with tqdm(total=l) as pbar:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=100)
        futures = [
            executor.submit(
                request_gpt, client, prompt, model, temperature, response_format, seed
            )
            for prompt in prompts
        ]
        for _ in concurrent.futures.as_completed(futures):
            pbar.update(1)
    concurrent.futures.wait(futures)
    return [future.result() for future in futures]


def multithread_embeddings(client, texts):
    l = len(texts)
    with tqdm(total=l) as pbar:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=100)
        futures = [executor.submit(get_embedding, client, text) for text in texts]
        for _ in concurrent.futures.as_completed(futures):
            pbar.update(1)
    concurrent.futures.wait(futures)
    return [future.result() for future in futures]


def get_embedding(client, text, model="text-embedding-3-small"):
    enc = tiktoken.encoding_for_model(model)
    # print("tokens: ", len(enc.encode(text)), len(enc.encode(text)) > 8191)
    while len(enc.encode(text)) > 8191:
        text = text[:-100]
        print("truncated: ", len(enc.encode(text)))
    try:
        return client.embeddings.create(input=[text], model=model).data[0].embedding
    except Exception as e:
        print(e)
        return get_embedding(client, text, model)


def cluster(X):
    if len(X) == 1:
        return [1]
    X = np.array(X)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=0.5,
        metric="cosine",
        linkage="average",
    ).fit(X)
    return list(map(lambda label: int(label), clustering.labels_))


def cluster_topic_assignments(client, clusters, texts):
    cluster_texts = defaultdict(list)
    for cluster, text in zip(clusters, texts):
        cluster_texts[cluster].append(text)
    prompt_list = []
    cluster_list = []
    for cluster, texts in cluster_texts.items():
        prompt, response_format, extract_response_func = (
            topic_assignment_prompt_factory(texts)
        )
        prompt_list.append(prompt)
        cluster_list.append(cluster)
    responses = multithread_prompts(client, prompt_list, response_format="json")
    if response_format == "json":
        responses = [extract_response_func(i) for i in responses]

    cluster_topics = {
        cluster: response for cluster, response in zip(cluster_list, responses)
    }
    return cluster_topics


def topic_assignment_prompt_factory(texts):
    messages = [
        {
            "role": "system",
            "content": """You are a topic assignment system. The user will provide you with a list of texts. You need to assign one topic to summarize all of them. 
            The topic should be a simple noun-phrase. Only one topic should be generated.
            Reply with the JSON format: 
            {{
                topic: string 
            }}
            """,
        },
        {"role": "user", "content": "\n".join(texts)},
    ]

    def extract_response_func(response):
        response = json.loads(response)["topic"]
        return response

    response_format = "json"
    return messages, response_format, extract_response_func


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
