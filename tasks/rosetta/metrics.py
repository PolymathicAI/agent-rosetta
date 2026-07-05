from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from .typing import TaskMetricConfig, TaskMetricConfigList

if TYPE_CHECKING:
    from .typing import Metric, TaskMetric


def cavity_volume() -> TaskMetricConfig:
    cavity_volume_filter = """<CavityVolume name="cav_vol" confidence="0.0" />"""
    cavity_volume_protocol = """<Add filter="cav_vol" />"""

    return TaskMetricConfig(
        filters=cavity_volume_filter, protocols=cavity_volume_protocol
    )


def radius_of_gyration() -> TaskMetricConfig:
    rg_weight = """<Reweight scoretype="rg" weight="1.0" />"""
    return TaskMetricConfig(score_weights=rg_weight)


def buns() -> TaskMetricConfig:
    buns_weight = """<Reweight scoretype="buried_unsatisfied_penalty" weight="1.0" />"""
    return TaskMetricConfig(score_weights=buns_weight)


def per_residue_energy(scoretype: str) -> TaskMetricConfig:
    name = f"residue_{scoretype}"
    per_residue_metric = f"""
        <PerResidueEnergyMetric name="{name}" scoretype="{scoretype}" scorefxn="scoring_post" />
    """
    per_residue_protocol = f"""<Add metrics="{name}" />"""

    return TaskMetricConfig(
        simple_metrics=per_residue_metric, protocols=per_residue_protocol
    )


def core_residues() -> TaskMetricConfig:
    metric_name = "core_residues"
    selector_name = f"__{metric_name}"

    core_residues_selector = f"""
        <Layer name="{selector_name}" select_core="true" select_boundary="false" select_surface="false"/>
    """
    core_residues_metric = f"""<SelectedResiduesMetric name="core_residues" residue_selector="{selector_name}" rosetta_numbering="false" />"""
    core_residues_protocol = f"""<Add metrics="{metric_name}" />"""

    return TaskMetricConfig(
        residue_selectors=core_residues_selector,
        simple_metrics=core_residues_metric,
        protocols=core_residues_protocol,
    )


metric_fn_map: dict[Metric, TaskMetric] = {
    "cavity_volume": cavity_volume,
    "radius_of_gyration": radius_of_gyration,
    "buns": buns,
    "res_fa_rep": functools.partial(per_residue_energy, "fa_rep"),
    "res_rama_prepro": functools.partial(per_residue_energy, "rama_prepro"),
    "core_residues": core_residues,
}


def compose_metrics(metrics: list[Metric]) -> TaskMetricConfigList:
    return TaskMetricConfigList(configs=[metric_fn_map[metric]() for metric in metrics])
