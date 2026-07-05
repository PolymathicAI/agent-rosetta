from __future__ import annotations

import html
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic

import litellm
from omegaconf import OmegaConf

from .typing import ModelConfigT, QueryResults, QueryStats
from .utils.logging import logger

if TYPE_CHECKING:
    from litellm.utils import ModelResponse

    from .history import History


@dataclass(frozen=True)
class ModelConfig:
    name: str = None
    model_name: str = None

    context_window: str = None
    max_query_retries: int = None

    reasoning_tag: str | None = None
    reasoning_formatting: str | None = None
    parse_reasoning: bool | None = False


class Model(ABC, Generic[ModelConfigT]):
    def __init__(self, config: ModelConfigT):
        self.config = config

        self.queries = 0
        self.stats = QueryStats()

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def query_model(self, messages: list[dict]) -> tuple[QueryResults, QueryStats]:
        pass

    def query(self, history: History) -> QueryResults:
        messages = history.get_query(context_window=self.config.context_window)
        query_results, query_stats = self.query_model(messages)

        self.queries += 1
        self.stats += query_stats

        logger.info(f"Query stats:\n{query_stats.model_dump(mode='json')}")
        logger.info(f"Total stats:\n{self.stats.model_dump(mode='json')}")
        return query_results


@dataclass(frozen=True)
class LiteLLMModelConfig(ModelConfig):
    completion_args: dict = None


class LiteLLMModel(Model[LiteLLMModelConfig]):
    def __init__(self, config: LiteLLMModelConfig):
        super().__init__(config)
        self.completion_kwargs = OmegaConf.to_container(
            self.config.completion_args, resolve=True
        )

    def setup(self):
        pass

    def query_model(self, messages: list[dict]) -> tuple[QueryResults, QueryStats]:
        try:
            response: ModelResponse = litellm.completion(
                model=self.config.model_name,
                messages=messages,
                **self.completion_kwargs,
            )
            if response is None:
                raise ValueError("Completion call response is None")
            logger.info(f"Completion response:\n{response.model_dump(mode='json')}")
        except Exception as e:
            logger.error(f"Error during completion call:\n{e}")
            return (
                QueryResults(finish_reason="error", reasoning="", content=""),
                QueryStats(),
            )

        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        cost = response.get("cost", None) or usage.get("cost", None)
        if cost is None:
            try:
                cost = litellm.completion_cost(completion_response=response)
            except:
                logger.warning(
                    "Could not estimate cost for the response. Setting to $0.00 ."
                )
                cost = 0
        cost = round(cost, 6)

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        if finish_reason != "stop":
            pass
            logger.warning(
                f"Completion call finish reason is {finish_reason}, expected stop"
            )

        message = choice.message
        content = message.content or ""
        content = content.strip("\n ")
        content = html.unescape(content)
        if len(content) == 0:
            logger.warning("LLM completion response content is empty.")
        if content.endswith("</action"):
            content += ">"

        reasoning = ""
        reasoning += message.get("reasoning_content", "").strip("\n ")
        if self.config.parse_reasoning:
            pattern_template = r"<{reasoning_tag}>(?P<reasoning>.*?)</{reasoning_tag}>\s*(?P<content>.*)"

            reasoning_tag = re.escape(self.config.reasoning_tag)
            pattern_str = pattern_template.format(reasoning_tag=reasoning_tag)
            pattern = re.compile(pattern_str, re.DOTALL | re.IGNORECASE)
            match = pattern.match(content)
            if match:
                reasoning += match.group("reasoning")
                content = match.group("content")
            else:
                logger.warning(
                    "The response does not match the expected reasoning pattern,"
                    " ignoring reasoning."
                )
                content = content

        reasoning_tokens = 0
        token_details = usage.get("completion_tokens_details", None)
        if token_details:
            if hasattr(token_details, "reasoning_tokens"):
                reasoning_tokens = token_details.reasoning_tokens
        if reasoning_tokens == 0 and len(reasoning) > 0:
            try:
                reasoning_tokens = litellm.utils.token_counter(
                    model=self.config.model_name,
                    messages=[{"role": "assistant", "content": reasoning}],
                )
            except:
                pass
                logger.warning("Could not estimate reasoning tokens.")

        query_results = QueryResults(
            finish_reason=finish_reason, reasoning=reasoning, content=content
        )
        query_stats = QueryStats(
            prompt_tokens=prompt_tokens,
            reasoning_tokens=reasoning_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
        )
        return query_results, query_stats
