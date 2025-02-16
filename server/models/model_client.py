import os
import traceback
from time import sleep
from typing import Dict, Optional, Tuple

from autogen import UserProxyAgent, AssistantAgent
import autogen

from utils import extract_json_content

dirname = os.path.dirname(__file__)
relative_path = lambda filename: os.path.join(dirname, filename)


class Provider:
    LOCAL = "local"
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"


# factory class
class ModelClient:
    """
    Unified client for multiple LLM providers with AutoGen integration
    Supports OpenAI, Gemini, Claude, and local models via config management
    """

    def __init__(
            self,
            provider: str,
            name: str,
            model: str,
            temperature: float,
            system_message: str = "You are a helpful AI assistant",
            config_path: str = relative_path("client_config.json"),
            overrides: Optional[Dict] = None
    ):
        self.provider = provider
        self.name = name
        self.model = model
        self.temperature = temperature
        self.system_message = system_message
        self.config_path = config_path
        self.overrides = overrides or {}
        self.user_proxy, self.assistant = self._create_agents()

    # create a client based on
    def _create_agents(self) -> Tuple[UserProxyAgent, AssistantAgent]:
        """Create provider-specific agents with proper configuration"""
        config_list = self._load_provider_config()

        assistant = AssistantAgent(
            name=self.name,
            system_message=self.system_message,
            llm_config={
                "config_list": config_list,
                "temperature": self.temperature,
                "timeout": 600,
                "cache_seed": None, # remove this to use cache
                **self.overrides.get("llm_config", {})
            },
            **self.overrides.get("assistant_config", {})
        )

        if self.provider == Provider.LOCAL:
            user_proxy = UserProxyAgent(
                name="user_proxy",
                human_input_mode="NEVER",
                code_execution_config=False,
                llm_config={  # Add explicit LLM config
                    "config_list": [{
                        "api_base": "http://localhost:1234/v1",
                        "api_key": "NULL"
                    }]
                },
                **self.overrides.get("proxy_config", {})
            )
        else:
            user_proxy = UserProxyAgent(
                name="user_proxy",
                human_input_mode="NEVER",
                code_execution_config=False,
                **self.overrides.get("proxy_config", {})
            )

        return user_proxy, assistant

    def _load_provider_config(self) -> list:
        """Load configuration for the specified provider"""
        provider_filters = {
            "openai": {
                "model": [self.model],
                "api_type": ["openai"],
            },
            "gemini": {"model": [self.model], "api_type": ["google"]},
            "claude": {"model": [self.model], "api_type": ["anthropic"]},
            # "local": {"model": [self.model], "base_url": [self.overrides.get("base_url")]}
            "local": {"model": [self.model]}
        }

        if self.provider not in provider_filters:
            raise ValueError(f"Unsupported provider: {self.provider}")

        args = {
            "env_or_file": self.config_path,
            "filter_dict": provider_filters[self.provider]
        }

        return autogen.config_list_from_json(**args)


    def chat(self, message: str) -> str:
        # sleep 2s to avoid rate limiting from Google
        sleep(2)
        """Initiate chat session with context management"""
        try:
            result = self.user_proxy.initiate_chat(
                self.assistant,
                message=message,
                max_turns=1,
                clear_history=not self.overrides.get("keep_context", False)
            )
        except Exception as e:
            print(e)
        # If all return are JSON, we can potentially just do:
        # return extract_json_content(result.chat_history[1].get('content'))
        return result.chat_history[1].get('content')

# for testing
if __name__ == "__main__":

    def local_llm_test():
        try:
            client = ModelClient(
                Provider.LOCAL,
                "goal_decomposition_agent",
                "deepseek-r1-distill-qwen-14b",
                temperature=0,
                system_message="""
                               ** Context **
                               You are a text analytics task planner. 
                               Users have collected a dataset of documents. The user will describe a goal to achieve through some text analytics, and what they have done already.
                               ** Task **
                               Your task is to provide a single next step based on what the user have done so far.
                               ** Requirements **
                               Please specify the logical next step to take.
                               Ignore the practical steps such as data collection, cleaning or visualization.
                               Focus on the conceptual next step. If no further steps are needed, label the next step with "END".
                               For the parentIds, provide the ids of the steps that this step **directly** depends on in terms of input-output data.
                               You should reply with {n} different next steps, so the user can have more choices.
                               Reply with this JSON format. Do not wrap the json codes in JSON markers.
                                   {{
                                       "next_steps": [
                                           {{
                                               "id": (string),
                                               "label": (string) or "END"
                                               "description": (string)
                                               "explanation": (string, explain why this step is needed)
                                               "parentIds": (string[], ids of the steps that this step **directly** depends on)
                                           }}
                                           ... ({n} different next steps)
                                           ],
                                   }}""".format(
                    n=2
                ),
                overrides={}
            )

            user_message = "My goal is: {goal}".format(
                goal="'I need to construct a knowledge graph from a collection of documents from wikipedia.'")

            result = client.chat(user_message)
            print(result)
            json_results = extract_json_content(result)
            print(json_results)
        except Exception as e:
            print(traceback.format_exc())
            print(e)

    def openai_test():
        try:
            client = ModelClient(
                Provider.OPENAI,
                "goal_decomposition_agent",
                "gpt-4o-mini",
                temperature=0,
                system_message="""
                               ** Context **
                               You are a text analytics task planner. 
                               Users have collected a dataset of documents. The user will describe a goal to achieve through some text analytics, and what they have done already.
                               ** Task **
                               Your task is to provide a single next step based on what the user have done so far.
                               ** Requirements **
                               Please specify the logical next step to take.
                               Ignore the practical steps such as data collection, cleaning or visualization.
                               Focus on the conceptual next step. If no further steps are needed, label the next step with "END".
                               For the parentIds, provide the ids of the steps that this step **directly** depends on in terms of input-output data.
                               You should reply with {n} different next steps, so the user can have more choices.
                               Reply with this JSON format. Do not wrap the json codes in JSON markers.
                                   {{
                                       "next_steps": [
                                           {{
                                               "id": (string),
                                               "label": (string) or "END"
                                               "description": (string)
                                               "explanation": (string, explain why this step is needed)
                                               "parentIds": (string[], ids of the steps that this step **directly** depends on)
                                           }}
                                           ... ({n} different next steps)
                                           ],
                                   }}""".format(
                    n=2
                )
            )

            user_message = "My goal is: {goal}".format(
                goal="'I need to construct a knowledge graph from a collection of documents from wikipedia.'")

            result = client.chat(user_message)
            print(result)
            json_results = extract_json_content(result)
            print(json_results)
        except Exception as e:
            print(traceback.format_exc())
            print(e)

    def gemini_test():
        try:
            client = ModelClient(
                Provider.GEMINI,
                "goal_decomposition_agent",
                "gemini-2.0-flash-lite-preview-02-05",
                temperature=0,
                system_message="""
                               ** Context **
                               You are a text analytics task planner. 
                               Users have collected a dataset of documents. The user will describe a goal to achieve through some text analytics, and what they have done already.
                               ** Task **
                               Your task is to provide a single next step based on what the user have done so far.
                               ** Requirements **
                               Please specify the logical next step to take.
                               Ignore the practical steps such as data collection, cleaning or visualization.
                               Focus on the conceptual next step. If no further steps are needed, label the next step with "END".
                               For the parentIds, provide the ids of the steps that this step **directly** depends on in terms of input-output data.
                               You should reply with {n} different next steps, so the user can have more choices.
                               Reply with this JSON format. Do not wrap the json codes in JSON markers.
                                   {{
                                       "next_steps": [
                                           {{
                                               "id": (string),
                                               "label": (string) or "END"
                                               "description": (string)
                                               "explanation": (string, explain why this step is needed)
                                               "parentIds": (string[], ids of the steps that this step **directly** depends on)
                                           }}
                                           ... ({n} different next steps)
                                           ],
                                   }}""".format(
                    n=2
                ),
                overrides={
                    "llm_config": {
                        "json_output": True,
                    }
                }
            )

            user_message = "My goal is: {goal}".format(
                goal="'I need to construct a knowledge graph from a collection of documents from wikipedia.'")

            result = client.chat(user_message)
            print(result)
            json_results = extract_json_content(result)
            print(json_results)
        except Exception as e:
            print(traceback.format_exc())
            print(e)

    local_llm_test()
    openai_test()
    gemini_test()

