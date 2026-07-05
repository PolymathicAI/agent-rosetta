from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import ray
from paretoset import paretoset
from ray.actor import ActorHandle

from agent_rosetta.utils.logging import logger

from .tools.esmfold import ESMFold
from .utils.rmsd import measure_rmsd

if TYPE_CHECKING:
    from pathlib import Path

    from tasks.rosetta.pack_ncaa import PackNCAATask
    from tasks.rosetta.task import RosettaTask

    from .environment import RosettaEnvironment
    from .state import RosettaDesign
    from .typing import RosettaRewardFunction


def get_pareto_front(
    designs: list[RosettaDesign] = None,
    fields: list[str] = None,
    minimize: list[bool] = None,
) -> list[RosettaDesign]:
    logger.info(f"Computing Pareto front for fields: {fields}...")
    scores = pd.DataFrame(
        {field: [d.reward.get(field, np.nan) for d in designs] for field in fields}
    )

    mask = paretoset(scores, sense=["min" if m else "max" for m in minimize])
    size_front = np.sum(mask)
    logger.info(
        f"Selected {size_front} Pareto-efficient design(s) out of"
        f" {len(designs)} ({size_front / len(designs):.2%})"
    )

    for i, d in enumerate(designs):
        d.is_pareto_efficient = bool(mask[i])
    return designs


def get_rmsd_to_init(
    designs: list[RosettaDesign] = None, ref_pdb: str = None
) -> list[RosettaDesign]:
    logger.info("Computing RMSD to reference structure...")
    for d in designs:
        d.reward["rmsd_to_init"] = measure_rmsd(ref_pdb, d.pdb)
    return designs


def get_esmfold_metrics(
    designs: list[RosettaDesign] = None,
    esmfold: ESMFold | ActorHandle = None,
    ref_pdb: Path = None,
    esmfold_output_dir: Path | None = None,
) -> list[RosettaDesign]:
    logger.info("Computing ESMFold metrics...")

    batch_size = 32
    sequences = [d.aa1_sequence for d in designs]
    if isinstance(esmfold, ESMFold):
        esmfold_pdb, esmfold_ca_plddt = esmfold.predict_pdb(
            sequences=sequences, batch_size=batch_size
        )
    elif isinstance(esmfold, ActorHandle):
        esmfold_pdb, esmfold_ca_plddt = ray.get(
            esmfold.predict_pdb.remote(sequences=sequences, batch_size=batch_size)
        )
    else:
        raise ValueError(f"Unsupported esmfold type: {type(esmfold)}.")

    for design_idx, design in enumerate(designs):
        design_esmfold_pdb = esmfold_pdb[design_idx]

        design_pdb_path = design.pdb
        if design_pdb_path is None:
            esmfold_pdb_path = esmfold_output_dir / f"design_{design_idx}_esmfold.pdb"
        else:
            esmfold_pdb_path = design_pdb_path.with_name(
                design_pdb_path.stem + "_esmfold.pdb"
            )

        with esmfold_pdb_path.open("w") as f:
            f.write(design_esmfold_pdb)

        design.esmfold_pdb = esmfold_pdb_path
        design.reward["esmfold_ca_plddt"] = esmfold_ca_plddt[design_idx]
        design.reward["esmfold_rmsd_to_init"] = measure_rmsd(esmfold_pdb_path, ref_pdb)
    return designs


def fixed_backbone_sequence_design_reward(
    designs: list[RosettaDesign] = None,
    env: RosettaEnvironment = None,
    task: RosettaTask = None,
) -> list[RosettaDesign]:
    for design in designs:
        design.reward["total_score"] = design.get_total_energy()
    designs = get_rmsd_to_init(designs=designs, ref_pdb=env.ref_pdb)
    designs = get_esmfold_metrics(
        designs=designs, esmfold=env.esmfold, ref_pdb=env.ref_pdb
    )

    designs = get_pareto_front(
        designs=designs,
        fields=["esmfold_ca_plddt", "esmfold_rmsd_to_init", "total_score"],
        minimize=[False, True, True],
    )
    return designs


def pack_ncaa_reward(
    designs: list[RosettaDesign] = None,
    env: RosettaEnvironment = None,
    task: PackNCAATask = None,
) -> list[RosettaDesign]:
    for design in designs:
        design.reward["total_score"] = design.get_total_energy()
        design.reward["cav_vol"] = design.score_dict.get("cav_vol", np.nan)
        design.reward["rg"] = design.score_dict.get("rg", np.nan)

        core_residues = design.score_dict.get("core_residues", "")
        if core_residues == "":
            core_residues = None
        else:
            core_residues = core_residues.replace("A", "").split(",")
            core_residues = list(map(lambda r: int(r), core_residues))
        design.reward["core_residues"] = core_residues

        ncaa_code3 = task.ncaa.code3
        ncaa_residues = [
            res_idx + 1
            for res_idx, res in enumerate(design.sequence)
            if res == ncaa_code3
        ]
        ncaa_core_residues = [
            res_idx
            for res_idx in ncaa_residues
            if core_residues is not None and res_idx in core_residues
        ]

        design.reward["ncaa_residues"] = ncaa_residues
        design.reward["ncaa_core_residues"] = ncaa_core_residues
        design.reward["ncaa_count"] = len(ncaa_residues)
        design.reward["ncaa_core_count"] = len(ncaa_core_residues)
        design.reward["ncaa_core_success"] = int(design.reward["ncaa_core_count"] == 1)

    designs = get_rmsd_to_init(designs=designs, ref_pdb=env.ref_pdb)
    designs = get_pareto_front(
        designs=designs,
        fields=[
            "ncaa_core_success",
            "total_score",
            "cav_vol",
            "rg",
            "rmsd_to_init",
        ],
        minimize=[False, True, True, True, True],
    )
    return designs


task_reward_map: dict[str, RosettaRewardFunction] = {
    "fixed-backbone-sequence-design": fixed_backbone_sequence_design_reward,
    "pack-ncaa": pack_ncaa_reward,
}
