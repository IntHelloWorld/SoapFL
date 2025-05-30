# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import time
from abc import ABC, abstractmethod
from typing import Any, Dict

import openai
import tiktoken
from openai.types.chat import ChatCompletion

from camel.typing import ModelType
from chatdev.utils import log_online


class ModelBackend(ABC):
    r"""Base class for different model backends.
    May be OpenAI API, a local LLM, a stub for unit tests, etc."""

    @abstractmethod
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        r"""Runs the query to the backend model.

        Raises:
            RuntimeError: if the return value from OpenAI API
            is not a dict that is expected.

        Returns:
            Dict[str, Any]: All backends must return a dict in OpenAI format.
        """
        pass


class OpenAIModel(ModelBackend):
    r"""OpenAI API in a unified ModelBackend interface."""

    def __init__(self, model_type: ModelType, model_config_dict: Dict) -> None:
        super().__init__()
        self.model_type = model_type
        self.model_config_dict = model_config_dict

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        string = "\n".join([message["content"] for message in kwargs["messages"]])
        encoding = tiktoken.encoding_for_model(self.model_type.value)
        num_prompt_tokens = len(encoding.encode(string))
        gap_between_send_receive = 15 * len(kwargs["messages"])
        num_prompt_tokens += gap_between_send_receive

        num_max_token_map = {
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "gpt-3.5-turbo-0613": 4096,
            "gpt-3.5-turbo-16k-0613": 16384,
            "gpt-3.5-turbo-1106": 16384,
            "gpt-4": 8192,
            "gpt-4-0613": 8192,
            "gpt-4-32k": 32768,
            "gpt-4o-2024-08-06": 128000,
        }
        num_max_token = num_max_token_map[self.model_type.value]
        num_max_completion_tokens = num_max_token - num_prompt_tokens
        if self.model_type == ModelType.GPT_4_O:
            num_max_completion_tokens = 16384
        elif self.model_type == ModelType.GPT_3_5_TURBO:
            num_max_completion_tokens = 4096
        self.model_config_dict['max_tokens'] = num_max_completion_tokens
        
        # set to your own OpenAI API key
        client = openai.OpenAI(
            base_url="",
            api_key="",
        )
        
        response = client.chat.completions.create(
            *args,
            **kwargs,
            model=self.model_type.value,
            **self.model_config_dict
        )
        # time.sleep(2)

        log_online(
            "**[OpenAI_Usage_Info Receive]**\nprompt_tokens: {}\ncompletion_tokens: {}\ntotal_tokens: {}\n".format(
                response.usage.prompt_tokens, response.usage.completion_tokens,
                response.usage.total_tokens))
        if not isinstance(response, ChatCompletion):
            raise RuntimeError("Unexpected return from OpenAI API")
        return response


class StubModel(ModelBackend):
    r"""A dummy model used for unit tests."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        ARBITRARY_STRING = "Lorem Ipsum"

        return dict(
            id="stub_model_id",
            usage=dict(),
            choices=[
                dict(finish_reason="stop",
                     message=dict(content=ARBITRARY_STRING, role="assistant"))
            ],
        )


class ModelFactory:
    r"""Factory of backend models.

    Raises:
        ValueError: in case the provided model type is unknown.
    """

    @staticmethod
    def create(model_type: ModelType, model_config_dict: Dict) -> ModelBackend:
        default_model_type = ModelType.GPT_3_5_TURBO

        if model_type in {
            ModelType.GPT_3_5_TURBO, ModelType.GPT_4, ModelType.GPT_4_32k, ModelType.GPT_4_O,
            None
        }:
            model_class = OpenAIModel
        elif model_type == ModelType.STUB:
            model_class = StubModel
        else:
            raise ValueError("Unknown model")

        if model_type is None:
            model_type = default_model_type

        # log_online("Model Type: {}".format(model_type))
        inst = model_class(model_type, model_config_dict)
        return inst
