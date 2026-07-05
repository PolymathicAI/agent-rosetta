from __future__ import annotations

import re
from typing import Literal, TypeAlias

from pydantic import BaseModel, field_validator, model_validator

from .utils import normalize_restypes

simple_aa_comp_shape: TypeAlias = Literal["OUTSIDE", "ABOVE", "BELOW"]
simple_aa_comp_boundary: TypeAlias = Literal["CONSTANT", "LINEAR", "QUADRATIC"]


class SimpleAACompBlock(BaseModel):
    type: str
    shape: simple_aa_comp_shape
    target: int | float
    radius: int | float | None = None
    boundary: simple_aa_comp_boundary
    strength: int

    @field_validator("type", mode="before")
    @classmethod
    def normalize_restype(cls, v: str) -> str:
        norm_v = normalize_restypes(v, separator=" ")
        if not norm_v:
            raise ValueError(f"No valid restypes found in '{v}'")
        return norm_v

    @model_validator(mode="after")
    def check_radius(self) -> SimpleAACompBlock:
        if self.shape == "outside" and self.radius is None:
            raise ValueError("RADIUS is required when SHAPE is OUTSIDE")
        return self

    @staticmethod
    def from_body(body: str) -> SimpleAACompBlock:
        keys = ["TYPE", "SHAPE", "TARGET", "RADIUS", "BOUNDARY", "STRENGTH"]

        keys_pattern = "|".join(keys)
        text_pattern = rf"""^(?P<key>{keys_pattern})\b\s+(?P<value>.+)"""
        text_regex = re.compile(text_pattern, re.MULTILINE | re.VERBOSE)

        block_dict = {}
        for match in text_regex.finditer(body):
            key = match.group("key").lower().strip()
            value = match.group("value").strip()
            block_dict[key] = value

        return SimpleAACompBlock(**block_dict)

    def to_aacomp_block(self) -> str:
        type = self.type
        shape = self.shape
        target = self.target
        radius = self.radius
        boundary = self.boundary
        strength = self.strength

        is_integer = isinstance(target, int) or (
            isinstance(target, float) and target.is_integer()
        )

        offset = 1 if is_integer else 0.05
        radius = radius if shape == "OUTSIDE" else 0

        if is_integer:
            target = int(target)
            radius = int(radius)
            target_key = "ABSOLUTE"
            delta_key = "DELTA"
        else:
            target_key = "FRACTION"
            delta_key = "FRACT_DELTA"

        delta = radius + offset
        delta_start, delta_end = -delta, delta

        before_function = boundary
        after_function = boundary
        strength = max(int(float(strength)), 1)
        num_penalties = delta_end - delta_start + 1 if is_integer else 3
        penalties = [0] * num_penalties
        if shape == "OUTSIDE":
            penalties[0] = strength
            penalties[-1] = strength
        if shape == "BELOW":
            penalties[0] = strength
            after_function = "CONSTANT"
        if shape == "ABOVE":
            penalties[-1] = strength
            before_function = "CONSTANT"
        penalties = " ".join(map(str, penalties))

        if is_integer:
            delta_start_line = f"{delta_key}_START {delta_start:.0f}"
            delta_end_line = f"{delta_key}_END {delta_end:.0f}"
        else:
            delta_start_line = f"{delta_key}_START {delta_start:.2f}"
            delta_end_line = f"{delta_key}_END {delta_end:.2f}"

        return "\n".join(
            [
                "PENALTY_DEFINITION",
                f"TYPE {type}",
                f"{target_key} {target}",
                delta_start_line,
                delta_end_line,
                f"PENALTIES {penalties}",
                f"BEFORE_FUNCTION {before_function}",
                f"AFTER_FUNCTION {after_function}",
                "END_PENALTY_DEFINITION",
            ]
        )
