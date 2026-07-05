from dataclasses import dataclass
from enum import Enum
from typing import Literal, TypeAlias

rosettascripts_mode: TypeAlias = Literal["cxx11thread", "mpi"]


@dataclass(frozen=True)
class LLMProviderConfig:
    name: str
    api_key_env_var: str


class LLMProvider(Enum):
    OPENROUTER = LLMProviderConfig("OpenRouter", "OPENROUTER_API_KEY")
    ANTHROPIC = LLMProviderConfig("Anthropic", "ANTHROPIC_API_KEY")
    OPENAI = LLMProviderConfig("OpenAI", "OPENAI_API_KEY")
    GOOGLE_AI_STUDIO = LLMProviderConfig("Google AI Studio", "GEMINI_API_KEY")
    OTHER = LLMProviderConfig("Other", "")
