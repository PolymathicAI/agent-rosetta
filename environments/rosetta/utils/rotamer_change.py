from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from environments.rosetta.actions import CompositionalPenalty, ResidueRestriction


def prepare_residue_restrictions(
    restrictions: list[ResidueRestriction],
) -> tuple[list[str], list[str]]:
    restrict_template = """
        <RestrictToSpecifiedBaseResidueTypes name="{restriction_name}" base_types="{residues}" selector="{selector_name}" />
    """
    prohibit_template = """
        <ProhibitSpecifiedBaseResidueTypes name="{restriction_name}" base_types="{residues}" selector="{selector_name}" />
    """

    task_operations, operations_names = [], []
    for restriction_idx, restriction in enumerate(restrictions):
        restriction_name = f"restriction_{restriction_idx}"

        restriction_type = restriction.restriction_type
        residues = restriction.residues
        selector_name = restriction.selector_name

        if restriction_type == "restrict":
            template = restrict_template
        elif restriction_type == "prohibit":
            template = prohibit_template

        operation = template.format(
            restriction_name=restriction_name,
            residues=residues,
            selector_name=selector_name,
        ).strip()

        task_operations.append(operation)
        operations_names.append(restriction_name)
    return task_operations, operations_names


def prepare_packing_restrictions(restrictions: str) -> tuple[list[str], list[str]]:
    restrict_template = """
        <OperateOnResidueSubset name="{restriction_name}" selector="{selector_name}">
            <RestrictToRepackingRLT />
        </OperateOnResidueSubset>
    """

    task_operations, operations_names = [], []
    selectors = [s for s in restrictions.split(",") if s]
    for restriction_idx, selector_name in enumerate(selectors):
        restriction_name = f"packing_restriction_{restriction_idx}"

        operation = restrict_template.format(
            restriction_name=restriction_name,
            selector_name=selector_name,
        ).strip()

        task_operations.append(operation)
        operations_names.append(restriction_name)
    return task_operations, operations_names


def prepare_comp_penalties(
    penalties: list[CompositionalPenalty] = None, workdir: Path = None
) -> tuple[list[str], list[str]]:
    mover_template = """
        <AddCompositionConstraintMover name="{mover_name}" filename="{comp_path}" {selector_name} />
    """
    protocol_template = """<Add mover="{mover_name}" />"""

    comp_dir = workdir / "aa_comps"
    comp_dir.mkdir(exist_ok=True)

    movers, protocols = [], []
    for penalty_idx, penalty in enumerate(penalties):
        comp = penalty.comp
        selector_name = penalty.comp_selector_name

        comp_path = comp_dir / f"aa_comp_{penalty_idx}.comp"
        with comp_path.open("w") as f:
            f.write(comp)

        mover_name = f"aa_comp_{penalty_idx}"
        mover = mover_template.format(
            mover_name=mover_name,
            comp_path=comp_path,
            selector_name=(f'selector="{selector_name}"' if selector_name else ""),
        ).strip()
        protocol_mover = protocol_template.format(mover_name=mover_name).strip()

        movers.append(mover)
        protocols.append(protocol_mover)
    return movers, protocols
