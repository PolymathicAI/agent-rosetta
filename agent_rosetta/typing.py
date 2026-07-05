from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from .environment import Environment, EnvironmentConfig
    from .model import Model, ModelConfig
    from .parser import Parser, ParserConfig
    from .runner import Runner, RunnerConfig
    from .task import Task, TaskConfig

EnvironmentConfigT = TypeVar("EnvironmentConfigT", bound="EnvironmentConfig")
EnvironmentStateT = TypeVar("EnvironmentStateT", bound="EnvironmentState")
EnvironmentT = TypeVar(
    "EnvironmentT", bound="Environment[EnvironmentConfigT, EnvironmentStateT]"
)

TaskConfigT = TypeVar("TaskConfigT", bound="TaskConfig")
TaskT = TypeVar("TaskT", bound="Task[TaskConfigT]")

ModelConfigT = TypeVar("ModelConfigT", bound="ModelConfig")
ModelT = TypeVar("ModelT", bound="Model[ModelConfigT]")

ParserConfigT = TypeVar("ParserConfigT", bound="ParserConfig")
ParserT = TypeVar("ParserT", bound="Parser[ParserConfigT]")

RunnerConfigT = TypeVar("RunnerConfigT", bound="RunnerConfig")
RunnerT = TypeVar("RunnerT", bound="Runner[RunnerConfigT]")

StatusCode: TypeAlias = Literal["none", "success", "error"]
MessageRole: TypeAlias = Literal["none", "system", "user", "assistant"]
MessageTag: TypeAlias = Literal["none", "success", "error"]
FinishReason: TypeAlias = Literal[
    "none", "error", "stop", "length", "tool_calls", "content_filter", "function_call"
]
ActionTag: TypeAlias = Literal["none", "choose", "run", "stop"]


class EnvironmentState(BaseModel):
    global_step: int | None = None
    status_code: StatusCode = "none"
    stderr: str | None = None


class Message(BaseModel):
    role: MessageRole = "none"
    tag: MessageTag = "none"
    reasoning: str | None = None
    content: str | None = None


class QueryResults(BaseModel):
    finish_reason: FinishReason = "none"
    reasoning: str | None = None
    content: str | None = None


class QueryStats(BaseModel):
    prompt_tokens: int = 0
    reasoning_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0

    def __add__(self, other: QueryStats) -> QueryStats:
        return QueryStats(
            **{k: getattr(self, k) + getattr(other, k) for k in QueryStats.model_fields}
        )


class ParserOutput(BaseModel):
    act_name: str | None = None
    act_tag: ActionTag = "none"
    act_args: BaseModel | None = None


class TrajectoryStep(BaseModel):
    state: EnvironmentState | None = None
    message: Message | None = None
    query_results: QueryResults | None = None
    parser_output: ParserOutput | None = None
    observation: EnvironmentState | None = None
    execution_time: float | None = None

    @property
    def idx(self) -> int:
        return self.observation.global_step


class StopStep(TrajectoryStep):
    parser_output: ParserOutput = ParserOutput(act_tag="stop")


class TrajectoryNode(BaseModel):
    node_idx: int | None = None
    parent_idx: int | None = None
    step: TrajectoryStep | None = None


class TrajectoryData(BaseModel):
    nodes: dict[int, TrajectoryNode] | None = None
    path: list[int] | None = None
