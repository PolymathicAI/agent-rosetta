from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from agent_rosetta.history import History
from environments.rosetta.actions import RosettaActions

from .task import RosettaTask
from .utils import (
    get_comp_penalty,
    get_initial_state,
    get_per_residue_score_summary,
    summarize_metric,
    summarize_structural_metrics,
)

if TYPE_CHECKING:
    from pathlib import Path

    from agent_rosetta.agent import Agent
    from environments.rosetta.environment import RosettaEnvironment
    from environments.rosetta.state import RosettaDesign

    from .task import RosettaTaskConfig


class FixedBackboneSequenceDesignTask(RosettaTask):
    structural_metrics = [
        "cav_vol",
        "rg",
        "buried_unsatisfied_penalty",
        "esmfold_rmsd_to_init",
        "esmfold_ca_plddt",
    ]
    summary_metrics = [
        "total_score",
        "cav_vol",
        "rg",
        "esmfold_rmsd_to_init",
        "esmfold_ca_plddt",
    ]

    q = 0.90
    k = 5

    def __init__(self, config: RosettaTaskConfig, workdir: Path = None):
        super().__init__(config, workdir=workdir)

    def build_history(
        self, env: RosettaEnvironment = None, agent: Agent = None
    ) -> History:
        system_prompt = env.config.system_prompt
        task_template = env.config.task_template

        task_prompt = self.config.prompt.strip()
        reasoning_formatting = agent.model.config.reasoning_formatting or ""

        messages = [
            {
                "role": "system",
                "content": system_prompt.format(
                    docs=RosettaActions.to_docs(),
                    reasoning_formatting=reasoning_formatting,
                ),
            },
            {
                "role": "user",
                "content": task_template.format(
                    prompt=task_prompt,
                    state=get_initial_state(env=env, metrics=self.structural_metrics),
                    action_formatting_instructions=self.get_action_formatting_instructions(
                        agent=agent, act_tag="choose"
                    ),
                ),
            },
        ]
        return History(messages)

    def summarize_ensemble(
        self, designs: list[RosettaDesign] = None, include_comp_penalty: bool = None
    ) -> str:
        template = textwrap.dedent("""
        - Number of designs: {n_designs} ({n_pareto} Pareto optimal)

        - Average total Rosetta energy: {score_mu:.2f} ± {score_std:.2f}

        {comp_penalty}

        {per_residue_summary}

        {structural_metrics}
        """).strip()

        n_designs, n_pareto = len(designs), sum(d.is_pareto_efficient for d in designs)
        score_mu, score_std = summarize_metric(designs=designs, metric="total_score")

        comp_penalty = get_comp_penalty(designs) if include_comp_penalty else ""
        per_residue_summary = get_per_residue_score_summary(
            designs=designs, fields=["fa_rep", "rama_prepro"], q=self.q, k=self.k
        )
        structural_metrics = summarize_structural_metrics(
            designs=designs, metrics=self.structural_metrics
        )

        return template.format(
            n_designs=n_designs,
            n_pareto=n_pareto,
            score_mu=score_mu,
            score_std=score_std,
            comp_penalty=comp_penalty,
            per_residue_summary=per_residue_summary,
            structural_metrics=structural_metrics,
        )
