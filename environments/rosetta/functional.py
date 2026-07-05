from __future__ import annotations

from typing import TYPE_CHECKING

from .typing import RosettaActionError, RosettaActionResults, RosettaCmdArgs
from .utils.act import run
from .utils.backbone_change import prepare_movemap_factory, prepare_mover
from .utils.rotamer_change import (
    prepare_comp_penalties,
    prepare_packing_restrictions,
    prepare_residue_restrictions,
)
from .utils.traj import get_successful_steps

if TYPE_CHECKING:
    from agent_rosetta.trajectory import Trajectory
    from tasks.rosetta.task import RosettaTask

    from .actions import (
        BackboneChangeArgs,
        GoBackToStepArgs,
        RotamerChangeArgs,
        ScorePDBArgs,
    )
    from .environment import RosettaEnvironment
    from .state import RosettaEnvironmentState
    from .typing import RosettaAction, RosettaActionFunction


def run_score_pdb(
    env: RosettaEnvironment = None,
    task: RosettaTask = None,
    workdir: str = None,
    act_args: ScorePDBArgs = None,
    traj: Trajectory | None = None,
) -> RosettaActionResults:
    ### Score functions ###
    scoring_weights = "\n".join(task.metrics_config.score_weights)

    ### Residue selectors ###
    residue_selectors = "\n".join(task.metrics_config.residue_selectors)

    ### Simple metrics ###
    simple_metrics = "\n".join(task.metrics_config.simple_metrics)

    ### Filters ###
    filters = "\n".join(task.metrics_config.filters)

    ### Movers ###
    movers = "\n".join(task.metrics_config.movers)

    relax_movemap_params = ""
    if task.config.relax_pre_score:
        relax_movemap_params = " ".join(
            f'{k}="{v}"' for k, v in task.config.relax_movemap_params.items()
        )

    ### Protocols ###
    relax_protocol = ""
    if task.config.relax_pre_score:
        relax_protocol = """<Add mover="relax" />"""

    protocols = "\n".join([relax_protocol, *task.metrics_config.protocols])

    cmd_args = RosettaCmdArgs(
        nstruct=1,
        use_mpi=False,
        cmd_mode="local",
        jd2_failed_job_exception=True,
        extra_res_fa=task.get_extra_res_fa(env.env_dir),
        native_pdb=env.ref_pdb,
    )
    return run(
        env=env,
        act_name="score_pdb",
        workdir=workdir,
        xml_args={
            "scoring_weights": scoring_weights,
            "additional_residue_types": task.additional_residue_types,
            "residue_selectors": residue_selectors,
            "simple_metrics": simple_metrics,
            "filters": filters,
            "movers": movers,
            "relax_movemap_params": relax_movemap_params,
            "protocols": protocols,
        },
        cmd_args=cmd_args,
    )


def run_rotamer_change(
    env: RosettaEnvironment = None,
    task: RosettaTask = None,
    act_args: RotamerChangeArgs = None,
    workdir: str = None,
    traj: Trajectory = None,
) -> RosettaActionResults:
    use_atom_pair_constraint = False
    if task.config.guidance_weights.get("atom_pair_constraint", None) is not None:
        if env.ref_pdb is None:
            raise RosettaActionError(
                "Reference PDB must be provided for atom pair constraints"
            )
        use_atom_pair_constraint = True

    ### Score functions ###
    guidance_weights = task.guidance_weights
    scoring_weights = "\n".join([guidance_weights, *task.metrics_config.score_weights])

    ### Residue selectors ###
    residue_selectors = "\n".join(
        [act_args.residue_selectors, *task.metrics_config.residue_selectors]
    )

    ### Task operations ###
    (
        residue_restriction_ops,
        residue_restriction_ops_names,
    ) = prepare_residue_restrictions(act_args.residue_restrictions)

    (
        packing_restriction_ops,
        packing_restriction_ops_names,
    ) = prepare_packing_restrictions(act_args.packing_restrictions)

    task_operations = "\n".join(
        [
            *residue_restriction_ops,
            *packing_restriction_ops,
        ]
    )
    task_operations_names = ",".join(
        [
            "include_current",
            *residue_restriction_ops_names,
            *packing_restriction_ops_names,
        ]
    )

    ### Simple metrics ###
    simple_metrics = "\n".join(task.metrics_config.simple_metrics)

    ### Filters ###
    filters = "\n".join(task.metrics_config.filters)

    ### Movers ###
    aa_comp_movers, aa_comp_protocols = prepare_comp_penalties(
        penalties=act_args.penalties, workdir=workdir
    )

    atom_pair_constraint_mover = ""
    if use_atom_pair_constraint:
        atom_pair_constraint_mover = """
        <AddConstraints name="geom_constraint">
            <AtomPairConstraintGenerator name="gen_geom_csts" ca_only="1" use_harmonic="1" native="1" />
        </AddConstraints>
        """

    movers = "\n".join(
        [
            *aa_comp_movers,
            atom_pair_constraint_mover,
            *task.metrics_config.movers,
        ]
    )

    ### Protocols ###
    pre_scoring_protocol = """<Add metrics="aa_composition_pre" />"""
    design_protocol = """<Add mover="design" />"""

    atom_pair_constraint_protocol = ""
    if use_atom_pair_constraint:
        atom_pair_constraint_protocol = """<Add mover="geom_constraint" />"""

    protocols = "\n".join(
        [
            *aa_comp_protocols,
            pre_scoring_protocol,
            atom_pair_constraint_protocol,
            design_protocol,
            *task.metrics_config.protocols,
        ]
    )

    cmd_args = RosettaCmdArgs(
        nstruct=task.config.nstruct,
        use_mpi=task.config.use_mpi,
        cmd_mode=task.config.mpi_mode if task.config.use_mpi else "local",
        jd2_failed_job_exception=not task.config.use_mpi,
        extra_res_fa=task.get_extra_res_fa(env.env_dir),
        native_pdb=env.ref_pdb,
    )
    return run(
        env=env,
        act_name="rotamer_change",
        xml_args={
            "guidance_weights": guidance_weights,
            "scoring_weights": scoring_weights,
            "additional_residue_types": task.additional_residue_types,
            "residue_selectors": residue_selectors,
            "task_operations": task_operations,
            "simple_metrics": simple_metrics,
            "filters": filters,
            "movers": movers,
            "task_operations_names": task_operations_names,
            "protocols": protocols,
        },
        cmd_args=cmd_args,
        workdir=workdir,
        slurm_options=task.config.slurm_options,
    )


def run_backbone_change(
    env: RosettaEnvironment = None,
    task: RosettaTask = None,
    act_args: BackboneChangeArgs = None,
    workdir: str = None,
    traj: Trajectory = None,
) -> RosettaActionResults:
    ### Score functions ###
    scoring_weights = "\n".join(task.metrics_config.score_weights)

    ### Residue selectors ###
    residue_selectors = "\n".join(
        [act_args.residue_selectors, *task.metrics_config.residue_selectors]
    )

    ### Movemap factories ###
    movemap_factory = prepare_movemap_factory(act_args)

    ### Simple metrics ###
    simple_metrics = "\n".join(task.metrics_config.simple_metrics)

    ### Filters ###
    filters = "\n".join(task.metrics_config.filters)

    ### Movers ###
    mover = prepare_mover(act_args)

    ### Protocols ###
    protocols = "\n".join(task.metrics_config.protocols)

    cmd_args = RosettaCmdArgs(
        nstruct=task.config.nstruct,
        use_mpi=task.config.use_mpi,
        cmd_mode=task.config.mpi_mode if task.config.use_mpi else "local",
        jd2_failed_job_exception=not task.config.use_mpi,
        extra_res_fa=task.get_extra_res_fa(env.env_dir),
        native_pdb=env.ref_pdb,
    )
    return run(
        env=env,
        act_name="backbone_change",
        xml_args={
            "scoring_weights": scoring_weights,
            "additional_residue_types": task.additional_residue_types,
            "residue_selectors": residue_selectors,
            "movemap_factories": movemap_factory,
            "simple_metrics": simple_metrics,
            "filters": filters,
            "movers": mover,
            "protocols": protocols,
        },
        cmd_args=cmd_args,
        workdir=workdir,
        slurm_options=task.config.slurm_options,
    )


def run_go_back_to_step(
    env: RosettaEnvironment = None,
    task: RosettaTask = None,
    workdir: str = None,
    act_args: GoBackToStepArgs = None,
    traj: Trajectory | None = None,
) -> RosettaActionResults:
    step = act_args.step

    steps = get_successful_steps(traj)

    if step < 0:
        raise ValueError(f"Invalid negative step number: {step}.")

    if step >= len(steps):
        raise ValueError(
            f"Invalid step number: {step}, greater than the total number of steps: {len(steps)}."
        )

    prev_step = steps[step]
    traj.go_back_to(prev_step)

    observation: RosettaEnvironmentState = prev_step.observation
    return RosettaActionResults(
        status_code=observation.status_code,
        stderr=observation.stderr,
        designs=observation.designs,
    )


act_fn_map: dict[RosettaAction, RosettaActionFunction] = {
    "score_pdb": run_score_pdb,
    "rotamer_change": run_rotamer_change,
    "backbone_change": run_backbone_change,
    "go_back_to_step": run_go_back_to_step,
}
