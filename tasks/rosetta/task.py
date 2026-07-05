from __future__ import annotations

import textwrap
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text

from agent_rosetta.task import Task, TaskConfig
from agent_rosetta.typing import Message, TrajectoryStep
from agent_rosetta.utils.logging import console, logger
from environments.rosetta.actions import ScorePDBArgs
from environments.rosetta.state import RosettaDesign
from environments.rosetta.tools.esmfold import ESMFold
from environments.rosetta.utils.traj import get_successful_steps
from tasks.rosetta.utils import summarize_steps

from .metrics import compose_metrics

if TYPE_CHECKING:
    from agent_rosetta.agent import Agent
    from agent_rosetta.trajectory import Trajectory
    from agent_rosetta.typing import ActionTag
    from environments.rosetta.environment import RosettaEnvironment
    from environments.rosetta.typing import CmdMode, RosettaAction

    from .typing import Metric, NCAAConfig, TaskMetricConfigList


@dataclass(frozen=True)
class RosettaTaskConfig(TaskConfig):
    initial_pdb: str = None

    nstruct: int = 1
    use_mpi: bool = False
    mpi_mode: CmdMode = "local"
    slurm_options: dict[str, float | str | None] = field(default_factory=dict)

    guidance_weights: dict[str, float] = field(default_factory=dict)

    metrics: list[Metric] = field(default_factory=list)

    relax_pre_score: bool = False
    relax_movemap_params: dict = field(default_factory=dict)

    tools: list[str] = field(default_factory=list)
    use_ray: bool = False

    use_ncaas: bool = False
    ncaas: list[NCAAConfig] = field(default_factory=list)


class RosettaTask(Task[RosettaTaskConfig]):
    structural_metrics: list[str]
    summary_metrics: list[str]
    q: float
    k: int

    def __init__(self, config: RosettaTaskConfig, workdir: Path = None):
        super().__init__(config, workdir=workdir)

    @property
    def additional_residue_types(self) -> str:
        template = """additional_residue_types="{}" """

        if len(self.config.ncaas) == 0:
            return ""

        additional_residue_types = ",".join([ncaa.code3 for ncaa in self.config.ncaas])
        return template.format(additional_residue_types)

    @property
    def guidance_weights(self) -> str:
        template = """<Reweight scoretype="{k}" weight="{v}" />"""
        return "\n".join(
            [template.format(k=k, v=v) for k, v in self.config.guidance_weights.items()]
        )

    @property
    def metrics_config(self) -> TaskMetricConfigList:
        return compose_metrics(self.config.metrics)

    def setup(self, env: RosettaEnvironment) -> TrajectoryStep | None:
        ### Load tools ###
        if "esmfold" in self.config.tools:
            with console.status(
                Text("Loading ESMFold", style="grey37"),
                spinner="dots",
                spinner_style="grey37",
                refresh_per_second=4,
            ):
                logger.info("Loading ESMFold...")

                if self.config.use_ray:
                    raise NotImplementedError
                else:
                    esmfold = ESMFold(log_filename="esmfold.log")

                env.esmfold = esmfold

        ### Make timing file and write header ###
        with (self.workdir / "timing.txt").open("w") as f:
            f.write("step,action_name,exit_code,start_time,end_time\n")

        ### Copy initial PDB file to workdir ###
        with Path(self.config.initial_pdb).expanduser().open("r") as f:
            initial_pdb = f.read()

        pdb_path = self.workdir / "init.pdb"
        with pdb_path.open("w") as f:
            f.write(initial_pdb)

        ### Set initial designs and reference structure in environment state ###
        env.state.global_step = -1
        env.state.designs = [
            RosettaDesign(pdb=pdb_path, score_dict={}, is_pareto_efficient=True)
        ]
        env.ref_pdb = pdb_path

        ### Score initial structure ###
        start_time = time.time()
        state = env.get_state()
        observation = env.step(
            act_name="score_pdb", act_args=ScorePDBArgs(), act_tag="run", task=self
        )
        end_time = time.time()

        return TrajectoryStep(
            state=state,
            message=None,
            query_results=None,
            parser_output=None,
            observation=observation,
            execution_time=end_time - start_time,
        )

    def build_history(self):
        raise NotImplementedError(
            "Subclasses of RosettaTask should implement build_history()"
        )

    def get_action_formatting_instructions(
        self, agent: Agent = None, act_tag: ActionTag = None
    ) -> str:
        if act_tag == "choose":
            action_formatting = textwrap.dedent("""
                <action tag="choose">
                <name>next_action_name</name>
                </action>
                """).strip("\n ")
        if act_tag == "run":
            action_formatting = textwrap.dedent("""
                <action tag="run">
                <name>action_name</name>
                <arg_name1>arg_value1</arg_name1>
                <arg_name2>arg_value2</arg_name2>
                ...
                </action>
                """).strip("\n ")

        if agent.model.config.reasoning_formatting:
            instructions_template = textwrap.dedent("""
                - First, you must {reasoning_formatting}
                - Then, write your action in the following format

                {action_formatting}
                """)
            instructions = instructions_template.format(
                reasoning_formatting=agent.model.config.reasoning_formatting.lower(),
                action_formatting=action_formatting,
            )
        else:
            instructions_template = textwrap.dedent("""
                You must write your action in the following format
                
                {action_formatting}

                Do not include any reasoning in your final response. Write valid action content only.
                """)
            instructions = instructions_template.format(
                action_formatting=action_formatting
            )
        return instructions.strip()

    @abstractmethod
    def summarize_ensemble(
        self, designs: list[RosettaDesign] = None, include_comp_penalty: bool = False
    ) -> str:
        pass

    def build_next_step_message(
        self, env: RosettaEnvironment, agent: Agent = None, traj: Trajectory = None
    ) -> Message:
        designs = env.state.designs

        last_step = traj[-1]
        last_act_tag = last_step.parser_output.act_tag
        last_act_name: RosettaAction = last_step.parser_output.act_name

        state, summary = "", ""
        if env.state.status_code == "success" and last_act_tag == "run":
            state = self.summarize_ensemble(
                designs=designs, include_comp_penalty=last_act_name == "rotamer_change"
            )
            summary = summarize_steps(traj=traj, metrics=self.summary_metrics)

        if last_act_tag == "choose":
            return Message(
                role="user",
                content=env.config.docs_template.format(
                    act_name=last_act_name,
                    docs=env.get_docs(last_act_name),
                    action_formatting_instructions=self.get_action_formatting_instructions(
                        agent=agent, act_tag="run"
                    ),
                ),
            )

        if env.state.status_code == "resource_error":
            logger.error(f"Resource error: {env.state.stderr}")
            raise RuntimeError(
                "The RosettaScripts environment encountered a resource error."
            )

        if env.state.status_code in ["validation_error", "runtime_error"]:
            return Message(
                role="user",
                tag="error",
                content=env.config.debug_template.format(
                    error=env.state.get_error_message(),
                    action_formatting_instructions=self.get_action_formatting_instructions(
                        agent=agent, act_tag="run"
                    ),
                ),
            )

        if env.state.status_code == "timeout":
            return Message(
                role="user",
                tag="error",
                content=env.config.timeout_template.format(
                    timeout=env.config.timeout,
                    action_formatting_instructions=self.get_action_formatting_instructions(
                        agent=agent, act_tag="run"
                    ),
                ),
            )

        steps = get_successful_steps(traj)

        if last_act_name == "go_back_to_step":
            header = "The RosettaScripts environment was successfully reset to a previous state:"

            last_step = steps[-1]
            last_act_name: RosettaAction = last_step.parser_output.act_name
        else:
            header = "The RosettaScripts environment successfully executed your action:"

        return Message(
            role="user",
            tag="success",
            content=env.config.refine_template.format(
                header=header,
                step=len(steps) - 1,
                act_name=last_act_name,
                state=state,
                summary=summary,
                action_formatting_instructions=self.get_action_formatting_instructions(
                    agent, "choose"
                ),
            ),
        )

    def get_extra_res_fa(self, env_dir: Path) -> str | None:
        if len(self.config.ncaas) == 0:
            return None
        return " ".join(
            [
                str(env_dir / "ncaas" / f"{ncaa.code3}.params")
                for ncaa in self.config.ncaas
            ]
        )
