from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .utils import normalize_restypes


class AACompBlock(BaseModel):
    restypes: str

    absolute: int | None = Field(default=None, ge=0)
    delta_start: int | None = None
    delta_end: int | None = None

    fraction: float | None = Field(default=None, ge=0, le=1)
    fract_delta_start: float | None = None
    fract_delta_end: float | None = None

    penalties: list[float]
    before_function: Literal["CONSTANT", "LINEAR", "QUADRATIC"]
    after_function: Literal["CONSTANT", "LINEAR", "QUADRATIC"]

    @field_validator("restypes", mode="before")
    @classmethod
    def normalize_restype(cls, v: str) -> str:
        normalized_restypes = normalize_restypes(v, separator=" ")
        if normalized_restypes == "":
            raise ValueError(f"No valid restypes found in {v}")
        return normalized_restypes

    @model_validator(mode="after")
    def check_target(self) -> AACompBlock:
        if self.absolute is None and self.fraction is None:
            raise ValueError("Either ABSOLUTE or FRACTION target must be specified")

        if self.absolute is not None and self.fraction is not None:
            raise ValueError("Only one of ABSOLUTE or FRACTION target can be specified")
        return self

    @model_validator(mode="after")
    def check_absolute(self) -> AACompBlock:
        if self.absolute is None:
            return self

        if self.fract_delta_start is not None or self.fract_delta_end is not None:
            raise ValueError(
                "FRACT_DELTA_START and FRACT_DELTA_END cannot be specified when"
                " ABSOLUTE target is used"
            )

        if self.delta_start is None or self.delta_end is None:
            raise ValueError(
                "DELTA_START and DELTA_END must be specified when ABSOLUTE target is"
                " used"
            )
        return self

    @model_validator(mode="after")
    def check_fraction(self) -> AACompBlock:
        if self.fraction is None:
            return self

        if self.delta_start is not None or self.delta_end is not None:
            raise ValueError(
                "DELTA_START and DELTA_END cannot be specified when FRACTION target is"
                " used"
            )

        if self.fract_delta_start is None or self.fract_delta_end is None:
            raise ValueError(
                "FRACT_DELTA_START and FRACT_DELTA_END must be specified when FRACTION"
                " target is used"
            )
        return self

    @model_validator(mode="after")
    def check_penalties(self) -> AACompBlock:
        if self.absolute is None:
            return self

        expected_num_penalties = self.delta_end - self.delta_start + 1
        if len(self.penalties) != expected_num_penalties:
            raise ValueError(
                "Number of penalties must be equal to DELTA_END - DELTA_START + 1"
                f" ({expected_num_penalties}) when ABSOLUTE target is used"
            )
        return self

    def to_string(self) -> str:
        if self.absolute is not None:
            target_lines = [
                f"ABSOLUTE {self.absolute}",
                f"DELTA_START {self.delta_start}",
                f"DELTA_END {self.delta_end}",
            ]
        if self.fraction is not None:
            target_lines = [
                f"FRACTION {self.fraction}",
                f"FRACT_DELTA_START {self.fract_delta_start}",
                f"FRACT_DELTA_END {self.fract_delta_end}",
            ]

        return "\n".join(
            [
                "PENALTY_DEFINITION",
                f"TYPE {self.restypes}",
                *target_lines,
                f"PENALTIES {' '.join(map(str, self.penalties))}",
                f"BEFORE_FUNCTION {self.before_function}",
                f"AFTER_FUNCTION {self.after_function}",
                "END_PENALTY_DEFINITION",
            ]
        )
