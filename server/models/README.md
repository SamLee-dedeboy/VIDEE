# LLM Multi-Agent Library

This library provides a unified interface for working with multiple Large Language Models (LLMs)—both local and remote. It simplifies model configuration, helps parse responses as valid JSON, and allows you to easily swap in new models.

## Overview

The LLM Multi-Agent Library makes it easy to:
- Configure multiple LLMs (OpenAI, Gemini, or local models).
- Use a common interface to send prompts and retrieve responses.
- Format responses as valid JSON consistently.
- Switch out or add new LLMs by editing a single configuration file (client_config.json).

Key benefits:
- No need to manually initialize each client (OpenAI, Gemini, local, etc.) in your code.
- Automatic handling of JSON response formatting with minimal boilerplate.
- Centralized credential and model configuration for all your LLMs.


## Configuration file - client_config.json
The library loads model details, like model name, type, API key, etc., from a JSON file—by default, `client_config.json`. A minimal example:
```json
{
  "models": [
    {
        "model": "gpt-4o-mini",
        "api_key": "<Replace With OpenAI API Key>",
        "api_type": "openai"
    },
    {
        "model": "gemini-2.0-flash",
        "api_key": "<Replace With Gemini API Key>",
        "api_type": "google"
    },
    {
        "model": "deepseek-r1-distill-qwen-14b",
        "api_key": "placeholder",
        "base_url": "http://localhost:1234/v1"
    },
  ]
}
```
-	`api_type`: Can be "openai", "gemini", or "local".
-	`model`: The actual model name to be used by the LLM provider.
-	`api_key`: Required if the LLM type is "openai" or "gemini".
-	`base_url`: For local models only, specify the path to LM Studio’s executable and port.

## Quick Start - OpenAI
1. Install new dependencies with `pip install -r server/requirements.txt`
2. Setting Up API Keys
  - OpenAI: Add your API key in the api_key field under the openai model configuration
```json
{
  "name": "openai_gpt35",
  "api_type": "openai",
  "model": "gpt-3.5-turbo",
  "api_key": "YOUR_OPENAI_API_KEY" // or omit and rely on OPENAI_API_KEY env variable
}
```

3. Replacing Your Current Code

Previously, you might manually initialize the OpenAI client like so in the query.py:
```py
# --- OLD code ---
model_client = OpenAIChatCompletionClient(
    model="gpt-3.5-turbo",
    api_key=api_key,
    temperature=0.0,
    model_capabilities={
        "vision": False,
        "function_calling": False,
        "json_output": True,
    },
)

# Then create an agent manually
decomposition_self_evaluation_agent = AssistantAgent(
    name="decomposition_self_evaluation_agent",
    model_client=model_client,
    system_message="** Context ** ..."
)

# Then parse the response
user_message = "My goal is: {goal}".format(goal=goal)
response = await decomposition_self_evaluation_agent.on_messages(
    [TextMessage(content=user_message, source="user")],
    cancellation_token=CancellationToken()
)
return json.loads(response.chat_message.content)["evaluation_score"]
```

With the LLM Multi-Agent Library, you can do the following (You can also check the test functions under model_client.py).
Note I wrote a util function to correctly parse JSON as well.

```py
# --- NEW code ---
# create the OpenAI gpt client
client = ModelClient(
    Provider.OPENAI,
    "goal_decomposition_agent",
    "gpt-4o-mini",
    temperature=0,
    system_message="** Context ** .."
)

user_message = "My goal is I need to construct a knowledge graph from a collection of documents from wikipedia"
# do chat
result = client.chat(user_message)
# parse it to json
json_results = extract_json_content(result)
```
With the above code you are able to get a perfect JSON output.


## Quick start - Gemini
1. Install new dependencies with `pip install -r server/requirements.txt`
2. Register an account on Google AI studio (https://aistudio.google.com), and generate a new API key.
  
  Gemini has pretty good request per minute comparing to OpenAI. I use it for my dev/testing.
  
  Free tier can get:

| Model    | Request per minute | Request per day|
| -------- | ------- | ------- |
| gemini-2.0-flash  | 15    | 1500 |
| gemini-2.0-flash-lite  | 30    | 1500 |
| gemini-2.0-pro  | 2    | 50 |
| gemini-2.0-flash-thinking (reasoning)  | 10    | 1500 |

3. Simialr to OpenAI, provide your Gemini API key under the api_key fields.

```json
{
  "name": "my name",
  "type": "gemini",
  "model": "gemini-2.0-flash-lite",
  "api_key": "YOUR_GEMINI_API_KEY"
}
```

4. Similar to OpenAI, then you can use the below code to interact with the Model
```py
# --- NEW code ---
# create the Gemini client
client = ModelClient(
    Provider.GEMINI,
    "goal_decomposition_agent",
    "gemini-2.0-flash-lite-preview-02-05",
    temperature=0,
    system_message="** Context ** .."
)

user_message = "My goal is I need to construct a knowledge graph from a collection of documents from wikipedia"
# do chat
result = client.chat(user_message)
# parse it to json
json_results = extract_json_content(result)
```


## Quick start - Local Model Dev
1. Install new dependencies with `pip install -r server/requirements.txt`
2. Download and install LM Studio https://lmstudio.ai/download
3. On LM studio, install the model based on your machine config. I use this one: https://huggingface.co/lmstudio-community/DeepSeek-R1-Distill-Qwen-7B-GGUF
4. Run the model, potentially with custom config
5. LM studio default listens on `http://127.0.0.1:1234`. Change the client_config.json to include your model, in my case:
  ```json
    {
        "model": "deepseek-r1-distill-qwen-14b",
        "api_key": "placeholder",
        "base_url": "http://localhost:1234/v1"
    },
  ```
6. Similar to OpenAI, then you can use the below code to interact with the Model
```py
# --- NEW code ---
# create the Gemini client
client = ModelClient(
     Provider.LOCAL,
     "goal_decomposition_agent",
     "deepseek-r1-distill-qwen-14b",
     temperature=0,
     system_message="** Context ** .."
  )

user_message = "My goal is I need to construct a knowledge graph from a collection of documents from wikipedia"
# do chat
result = client.chat(user_message)
# parse it to json
json_results = extract_json_content(result)
```

