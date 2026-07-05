from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import numpy as np
from tabulate import tabulate

from environments.rosetta.constants.score import SCORE_SYNONYMS
from environments.rosetta.utils.traj import get_successful_steps

if TYPE_CHECKING:
    from agent_rosetta.typing import Trajectory
    from environments.rosetta.environment import RosettaEnvironment
    from environments.rosetta.state import RosettaDesign, RosettaEnvironmentState

metric_name_map: dict[str, str] = {
    "total_score": "Total Rosetta energy",
    "cav_vol": "Cavity volume (Å^3)",
    "rg": "Radius of gyration (Å)",
    "buried_unsatisfied_penalty": "Buried unsatisfied Hydrogen bonds penalty",
    "esmfold_rmsd_to_init": "ESMFold RMSD to init (Å)",
    "esmfold_ca_plddt": "ESMFold CA pLDDT",
}


def summarize_metric(
    designs: list[RosettaDesign] = None, metric: str = None
) -> tuple[float | None, float | None]:
    values = [d.metrics.get(metric, np.nan) for d in designs]
    values = np.array(values)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return None, None
    return np.mean(values), np.std(values)


def summarize_structural_metrics(
    designs: list[RosettaDesign] = None, metrics: list[str] = None
) -> str:
    template = textwrap.dedent("""
        - Structural metrics:
        
        {table}
        """)

    table = []
    for metric in metrics:
        name = metric_name_map.get(metric, metric)

        mean, std = summarize_metric(designs=designs, metric=metric)

        summary = f"{mean:.2f}"
        if std is not None:
            summary += f" ± {std:.2f}"

        table.append([f"{name}", summary])

    table_str = tabulate(table, tablefmt="plain")
    return template.format(table=table_str).strip()


def get_initial_state(env: RosettaEnvironment = None, metrics: list[str] = None) -> str:
    if len(env.state.designs) != 1:
        raise ValueError("Only a single design is supported as initial state.")

    design = env.state.designs[0]
    total_energy = design.get_total_energy()
    structural_metrics = summarize_structural_metrics(designs=[design], metrics=metrics)

    length_line = f"- Sequence length: {len(design.sequence)} residues"
    energy_line = f"- Total Rosetta energy: {total_energy:.2f}"
    return "\n".join([length_line, energy_line, structural_metrics])


def summarize_steps(traj: Trajectory = None, metrics: list[str] = None) -> str:
    steps = get_successful_steps(traj)

    headers = ["Step", "Action"]
    headers += [metric_name_map.get(metric, metric) for metric in metrics]
    table = []
    for step_idx, step in enumerate(steps):
        act_name = step.parser_output.act_name

        obs: RosettaEnvironmentState = step.observation
        designs = obs.designs

        row = [step_idx, act_name]
        for metric in metrics:
            mean, _ = summarize_metric(designs=designs, metric=metric)
            row.append(mean)
        table.append(row)

    return tabulate(
        table, headers=headers, tablefmt="github", floatfmt=".2f", missingval=""
    )


def summarize_per_residue_score_field(
    designs: list[RosettaDesign] = None,
    field: str = None,
    q: float = None,
    k: int = None,
) -> str:
    template = textwrap.dedent("""
        -- {score_name}:

        Average per-sequence {q:.0f}-th quantile: {score_q_quantile:.2f}

        {summary}
        """)

    n_designs = len(designs)

    seq_lengths = [len(d.sequence) for d in designs]
    assert len(set(seq_lengths)) == 1, "All designs must have the same length."
    seq_length = seq_lengths[0]

    n_res_types = len(set(sum([d.sequence for d in designs], [])))
    res_idx_map = {}

    score_value = np.full((n_designs, seq_length, n_res_types), np.nan, dtype=float)
    for i, design in enumerate(designs):
        for j, res in enumerate(design.sequence):
            if res in res_idx_map:
                res_idx = res_idx_map[res]
            else:
                res_idx = len(res_idx_map)
                res_idx_map[res] = res_idx

            score_value[i, j, res_idx] = design.score_dict.get(
                f"residue_{field}_{j + 1}", np.nan
            )

    score_q_quantile = np.nanquantile(score_value, q, axis=(1, 2), keepdims=True)
    score_mask = score_value >= score_q_quantile

    idx_res_map = {v: k for k, v in res_idx_map.items()}

    res_occurrence = np.amax(score_mask.astype(int), axis=1)  # (n_designs, n_res_types)
    res_occurrence = np.sum(res_occurrence, axis=0)  # (n_res_types,)
    res_occurrence = res_occurrence / n_designs

    summary_lines = []
    sorted_res_occurrence_idx = np.argsort(-res_occurrence)
    for res_idx in sorted_res_occurrence_idx[:k]:
        res = idx_res_map[res_idx]
        res_occurrence_value = res_occurrence[res_idx]
        if res_occurrence_value == 0:
            continue

        res_pos_occurrence = score_mask[..., res_idx]  # (n_designs, seq_length)
        res_pos_occurrence = np.sum(res_pos_occurrence, axis=0)  # (seq_length,)
        res_pos_occurrence = res_pos_occurrence / np.sum(res_pos_occurrence)

        sorted_res_pos_occurrence_idx = np.argsort(-res_pos_occurrence)
        sorted_res_pos_occurrence = res_pos_occurrence[sorted_res_pos_occurrence_idx]
        res_pos_mask = np.cumsum(sorted_res_pos_occurrence) >= q
        last_idx = np.argmax(res_pos_mask)

        positions = sorted_res_pos_occurrence_idx[: last_idx + 1] + 1
        positions = ",".join(map(str, positions))

        line = f"{res}: {res_occurrence_value:<7.2%} (positions: {positions})"
        summary_lines.append(line)

    return template.format(
        score_name=SCORE_SYNONYMS.get(field, field),
        q=q * 100,
        score_q_quantile=np.mean(score_q_quantile),
        summary="\n".join(summary_lines).strip(),
    ).strip()


def summarize_ncaa_inclusion(
    designs: list[RosettaDesign] = None, ncaa_code3: str = None, q: float = None
) -> str:
    template = textwrap.dedent("""
        - {ncaa_code3} inclusion summary:
        -- List of core residue indices after design: {core_residues}
        {ncaa_inclusion}{ncaa_core_inclusion}
        {most_common_ncaa_residues}{ncaa_score_summary}
        """)
    ncaa_inclusion_line_template = """-- Percentage of designs with at least one {ncaa_code3} residue: {ncaa_success:.2%} (min: {ncaa_min}, max: {ncaa_max})\n"""
    ncaa_core_inclusion_line_template = """-- Percentage of designs with exactly one {ncaa_code3} residue in the core: {ncaa_core_success:.2%} (min: {ncaa_core_min}, max: {ncaa_core_max})"""

    ncaa_count = np.array([d.reward.get("ncaa_count", np.nan) for d in designs])
    ncaa_count = ncaa_count[~np.isnan(ncaa_count)]
    ncaa_success = np.mean(ncaa_count > 0)
    ncaa_min, ncaa_max = min(ncaa_count), max(ncaa_count)
    ncaa_inclusion_line = ncaa_inclusion_line_template.format(
        ncaa_code3=ncaa_code3,
        ncaa_success=ncaa_success,
        ncaa_min=ncaa_min,
        ncaa_max=ncaa_max,
    )

    core_residues = [d.reward.get("core_residues", None) for d in designs]
    core_residues = [r for r in core_residues if r is not None]
    core_residues = sum(core_residues, [])
    core_residues = sorted(list(set(core_residues)))
    if len(core_residues) == 0:
        core_residues = (
            "RosettaScripts' Layer selector could not determine the core residues of"
            " any design structure. Success will be determined based on"
            f" {ncaa_code3} inclusion at any position."
        )
        ncaa_core_inclusion_line = ""
    else:
        core_residues = ",".join(map(str, core_residues))

        ncaa_core_count = np.array(
            [d.reward.get("ncaa_core_count", np.nan) for d in designs]
        )
        ncaa_core_count = ncaa_core_count[~np.isnan(ncaa_core_count)]
        ncaa_core_success = np.nanmean(
            [d.reward.get("ncaa_core_success", np.nan) for d in designs]
        )
        ncaa_core_min, ncaa_core_max = min(ncaa_core_count), max(ncaa_core_count)
        ncaa_core_inclusion_line = ncaa_core_inclusion_line_template.format(
            ncaa_code3=ncaa_code3,
            ncaa_core_success=ncaa_core_success,
            ncaa_core_min=ncaa_core_min,
            ncaa_core_max=ncaa_core_max,
        )

    most_common_ncaa_residues_line = ""
    ncaa_score_summary = ""
    if ncaa_success > 0:
        most_common_ncaa_residues_line_template = """-- Most common {ncaa_code3} residue positions: {most_common_ncaa_residues}\n"""

        seq_length = len(designs[0].sequence)
        ncaa_residue_occurrence = np.zeros(seq_length)
        for d in designs:
            design_ncaa_residue = d.reward.get("ncaa_residues", [])
            design_ncaa_residue_idx = [r - 1 for r in design_ncaa_residue]
            ncaa_residue_occurrence[design_ncaa_residue_idx] += 1
        ncaa_residue_occurrence /= np.sum(ncaa_residue_occurrence)

        sorted_ncaa_residue_idx = np.argsort(-ncaa_residue_occurrence)
        sorted_ncaa_residue_occurrence = ncaa_residue_occurrence[
            sorted_ncaa_residue_idx
        ]
        ncaa_residue_mask = np.cumsum(sorted_ncaa_residue_occurrence) >= q
        last_idx = np.argmax(ncaa_residue_mask)

        most_common_ncaa_residues = sorted_ncaa_residue_idx[: last_idx + 1] + 1
        most_common_ncaa_residues = ",".join(map(str, most_common_ncaa_residues))
        most_common_ncaa_residues_line = most_common_ncaa_residues_line_template.format(
            ncaa_code3=ncaa_code3, most_common_ncaa_residues=most_common_ncaa_residues
        )

        n_designs = len(designs)
        ncaa_score_summary_lines = []
        for field in ["fa_rep", "rama_prepro"]:
            score_line_template = """-- Average {score_field} at {ncaa_code3} residues: {score_mu:.2f} ± {score_std:.2f}"""

            score_value = np.full((n_designs, seq_length), np.nan, dtype=float)
            for i, design in enumerate(designs):
                design_ncaa_residues = design.reward.get("ncaa_residues", [])
                for pos in design_ncaa_residues:
                    score_value[i, pos - 1] = design.score_dict.get(
                        f"residue_{field}_{pos}", np.nan
                    )

            score_mu = np.nanmean(score_value)
            score_std = np.nanstd(score_value)
            ncaa_score_summary_lines.append(
                score_line_template.format(
                    score_field=SCORE_SYNONYMS.get(field, field),
                    ncaa_code3=ncaa_code3,
                    score_mu=score_mu,
                    score_std=score_std,
                ).strip()
            )
        ncaa_score_summary = "\n".join(ncaa_score_summary_lines + [""]).strip()

    return template.format(
        ncaa_code3=ncaa_code3,
        core_residues=core_residues,
        ncaa_inclusion=ncaa_inclusion_line,
        ncaa_core_inclusion=ncaa_core_inclusion_line,
        most_common_ncaa_residues=most_common_ncaa_residues_line,
        ncaa_score_summary=ncaa_score_summary,
    ).strip()


def get_comp_penalty(designs: list[RosettaDesign]) -> str:
    comp_penalty_template = textwrap.dedent("""
        - Average compositional before design {pre_comp_mu:.2f}, and after design {comp_mu:.2f} ({comp_delta:+.2f})
        """)

    pre_comp_mu, _ = summarize_metric(designs=designs, metric="aa_composition_pre")
    comp_mu, _ = summarize_metric(designs=designs, metric="aa_composition")

    if pre_comp_mu is None or comp_mu is None:
        return ""

    return comp_penalty_template.format(
        pre_comp_mu=pre_comp_mu,
        comp_mu=comp_mu,
        comp_delta=comp_mu - pre_comp_mu,
    ).strip("\n ")


def get_per_residue_score_summary(
    designs: list[RosettaDesign] = None,
    fields: list[str] = None,
    q: float = None,
    k: int = None,
) -> str:
    per_residue_summary_header_template = textwrap.dedent("""
        - Top-{k} most common outlier residue types. A residue is an outlier if its energy term is above the {q:.0f}-th quantile of the per-residue energy term for that design. For each outlier residue type, we include the most common outlier positions along the sequence (positions are 1-based):
        """)

    per_residue_summary_header = per_residue_summary_header_template.format(
        k=k, q=q * 100
    ).strip()

    per_residue_summary_body = [
        summarize_per_residue_score_field(designs=designs, field=field, q=q, k=k)
        for field in fields
    ]
    per_residue_summary_lines = [per_residue_summary_header] + per_residue_summary_body

    return "\n\n".join(per_residue_summary_lines).strip()
