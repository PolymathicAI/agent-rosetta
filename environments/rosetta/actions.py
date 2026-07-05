from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from agent_rosetta.action import EnvironmentActions

from .typing import BackboneMover, ResidueRestrictionType

rotamer_change_docs = """
Perform a Rosetta FastDesign action with design enabled to change the rotamers of the sequence without perturbing the backbone. This action combines residue selectors, compositional penalties, residue restrictions, and packing restrictions to guide the search process.

Arguments:
  - residue_selectors (string): the XML definitions of the residue selectors.
  - penalties (list): a list of compositional penalty definitions. Each item includes the following parameters:
    - comp (string): the penalty definition blocks specifying the compositional constraints.
    - comp_selector_name (string): the name of the residue selector to apply the compositional constraints to.
  - residue_restrictions (list): a list of residue restriction definitions. Each item includes the following parameters:
    - restriction_type (string): whether to `restrict` or `prohibit` residue types.
    - residues (string): the list of one- or three-letter residue codes separated by a comma.
    - selector_name (string): the name of the residue selector to apply the restriction to.
  - packing_restrictions (string): A list of residue selector names separated by commas.
"""

backbone_change_docs = """
Perturb the backbone conformation. This action implements three Rosetta backbone movers: `small`, `shear`, and `backrub`. Specify the mover to use with `mover_name`, the parameters of the mover in XML format with `mover_params`, and the residues to perturb with `residue_selector`.

Arguments:
  - mover_name (string): the name of the Rosetta backbone mover to use (can be `small`, `shear`, or `backrub`).
  - mover_params (string): the parameters of the mover in XML format.
  - residue_selectors (string): the XML definitions of the residue selectors.
  - mover_selector_name (string): the name of the residue selector to apply the mover to.
"""

go_back_to_step_docs = """
Revert the environment state to a previous step in the trajectory. This action resets the environment to the state at the end of the specified step, allowing you to retry actions or explore different paths.

Arguments:
  - step (integer): the number of the step to revert to, starting from 0.
"""


class ScorePDBArgs(BaseModel):
    pass


class CompositionalPenalty(BaseModel):
    comp: str = ""
    comp_selector_name: str = ""


class ResidueRestriction(BaseModel):
    restriction_type: ResidueRestrictionType
    residues: str
    selector_name: str


class RotamerChangeArgs(BaseModel):
    residue_selectors: str = ""
    penalties: list[CompositionalPenalty] = Field(default_factory=list)
    residue_restrictions: list[ResidueRestriction] = Field(default_factory=list)
    packing_restrictions: str = ""


class BackboneChangeArgs(BaseModel):
    residue_selectors: str = ""
    mover_name: BackboneMover
    mover_params: str = ""
    mover_selector_name: str = ""

    @field_validator("mover_name", mode="before")
    @classmethod
    def validate_mover_name(cls, v: str) -> str:
        return v.lower()


class GoBackToStepArgs(BaseModel):
    step: int


class RosettaActions(EnvironmentActions):
    ROTAMER_CHANGE = ("rotamer_change", RotamerChangeArgs, rotamer_change_docs)
    BACKBONE_CHANGE = ("backbone_change", BackboneChangeArgs, backbone_change_docs)
    GO_BACK_TO_STEP = ("go_back_to_step", GoBackToStepArgs, go_back_to_step_docs)
