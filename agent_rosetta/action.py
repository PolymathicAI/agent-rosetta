from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel


@dataclass(frozen=True)
class ActionSpec:
    name: str
    args: type[BaseModel]
    docs: str


class EnvironmentActions(Enum):
    value: ActionSpec

    def __new__(cls, name: str, args: type[BaseModel], docs: str):
        obj = object.__new__(cls)
        obj._value_ = ActionSpec(name, args, docs)
        return obj

    @classmethod
    def from_name(cls, act_name: str) -> EnvironmentActions:
        for act in cls:
            if act.value.name == act_name:
                return act
        raise ValueError(f"Invalid action name '{act_name}'")

    @classmethod
    def to_docs(cls):
        doc_lines = []
        for act in cls:
            spec = act.value
            doc_lines.append(f"- {spec.name}")
            doc_lines.append(f'"""{spec.docs}"""')
            doc_lines.append("")
        return "\n".join(doc_lines)

    @classmethod
    def from_act_args_dict(
        cls, act_name: str = None, act_args_dict: dict = None
    ) -> BaseModel:
        act = cls.from_name(act_name)

        act_spec = act.value
        ArgsModel = act_spec.args

        model = ArgsModel(**act_args_dict)
        return model
