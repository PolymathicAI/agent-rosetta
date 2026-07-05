from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

from agent_rosetta.utils.logging import logger
from environments.rosetta.state import RosettaDesign
from environments.rosetta.typing import RosettaActionError, RosettaActionResults

from .cmd import run_cmd_local, run_cmd_slurm

if TYPE_CHECKING:
    from pathlib import Path

    from environments.rosetta.environment import RosettaEnvironment
    from environments.rosetta.typing import (
        RosettaAction,
        RosettaCmdArgs,
        RosettaCmdResults,
        ScoreDict,
    )


def prepare_xml(
    env: RosettaEnvironment = None,
    act_name: RosettaAction = None,
    xml_args: dict = None,
    workdir: Path = None,
    suffix: str | None = None,
) -> Path:
    act_xml_template_path = env.env_dir / "xml" / f"{act_name}.xml"
    if not act_xml_template_path.exists():
        raise FileNotFoundError(
            f"XML file for action '{act_name}' not found at {act_xml_template_path}"
        )

    with act_xml_template_path.open("r") as f:
        xml_template = f.read().strip()
    xml = xml_template.format(**xml_args)

    suffix_str = f"_{suffix}" if suffix else ""
    xml_path = workdir / f"{act_name}{suffix_str}.xml"
    with xml_path.open("w") as f:
        f.write(xml)
    return xml_path


def prepare_cmd(
    env: RosettaEnvironment = None,
    xml_path: Path = None,
    design_list_path: Path = None,
    cmd_args: RosettaCmdArgs = None,
    validate_and_exit: bool = None,
    workdir: Path = None,
    design_dir: Path = None,
    slurm_options: dict | None = None,
) -> tuple[Path, Path, Path]:
    cmd_template_path = env.env_dir / "scripts" / "cmd.sh"
    with cmd_template_path.open("r") as f:
        cmd_template = f.read().strip()

    suffix_str = f"_{cmd_args.suffix}" if cmd_args.suffix else ""
    if validate_and_exit:
        use_mpi = False
        mode = "local"
        suffix_str = f"{suffix_str}_val"

        pdb = env.state.designs[0].pdb
        nstruct_per_design = 1

        input_pdb = f"-in:file:s {pdb}"
        validate_and_exit_flag = "-validate_and_exit "
    else:
        use_mpi = cmd_args.use_mpi
        mode = cmd_args.cmd_mode

        with design_list_path.open("r") as f:
            n_designs = sum(1 for _ in f)
        nstruct_per_design = max(1, cmd_args.nstruct // n_designs)

        input_pdb = f"-in:file:l {design_list_path}"
        validate_and_exit_flag = ""

    nprocs = 1
    mpi_preamble = ""
    exec_path = env.config.exec_path
    if use_mpi:
        nprocs = cmd_args.nstruct + 2
        mpi_preamble = f"mpirun -n {nprocs} "
        exec_path = env.config.mpi_exec_path

    slurm_flags = []
    if mode == "slurm":
        if slurm_options is None:
            raise ValueError(
                "Slurm parameters must be provided when using 'slurm' mode."
            )

        for k, v in slurm_options.items():
            if v is None:
                slurm_flags.append(f"#SBATCH --{k}")
            else:
                k = k.replace("_", "-")
                if k == "ntasks":
                    v = nprocs
                slurm_flags.append(f"#SBATCH --{k}={v}")
    slurm_flags = "\n".join(slurm_flags).strip()

    native_pdb = ""
    if cmd_args.native_pdb is not None:
        native_pdb = f"-in:file:native {cmd_args.native_pdb}"

    extra_res_fa = ""
    if cmd_args.extra_res_fa is not None:
        extra_res_fa = f"-extra_res_fa {cmd_args.extra_res_fa}"

    cmd = cmd_template.format(
        slurm_flags=slurm_flags,
        mpi_preamble=mpi_preamble,
        exec_path=exec_path,
        validate_and_exit=validate_and_exit_flag,
        jd2_failed_job_exception=cmd_args.jd2_failed_job_exception,
        input_pdb=input_pdb,
        output_dir_score=workdir,
        output_dir_pdb=design_dir,
        nstruct=nstruct_per_design,
        xml_path=xml_path,
        native_pdb=native_pdb,
        extra_res_fa=extra_res_fa,
    )

    cmd_path = workdir / f"cmd{suffix_str}.sh"
    stdout_path = workdir / f"cmd{suffix_str}_stdout.log"
    stderr_path = workdir / f"cmd{suffix_str}_stderr.log"
    with cmd_path.open("w") as f:
        f.write(cmd)
    cmd_path.chmod(0o755)
    return cmd_path, stdout_path, stderr_path


def validate_cmd(
    env: RosettaEnvironment = None,
    xml_path: Path = None,
    design_list_path: Path = None,
    cmd_args: RosettaCmdArgs = None,
    workdir: Path = None,
    design_dir: Path = None,
) -> RosettaCmdResults:
    cmd_path, stdout_path, stderr_path = prepare_cmd(
        env=env,
        xml_path=xml_path,
        design_list_path=design_list_path,
        cmd_args=cmd_args,
        validate_and_exit=True,
        workdir=workdir,
        design_dir=design_dir,
    )
    cmd_results = run_cmd_local(
        cmd_path=cmd_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout=env.config.timeout,
    )
    return cmd_results


def run_cmd(
    env: RosettaEnvironment = None,
    xml_path: Path = None,
    design_list_path: Path = None,
    cmd_args: RosettaCmdArgs = None,
    workdir: Path = None,
    design_dir: Path = None,
    slurm_params: dict | None = None,
) -> RosettaCmdResults:
    cmd_path, stdout_path, stderr_path = prepare_cmd(
        env=env,
        xml_path=xml_path,
        design_list_path=design_list_path,
        cmd_args=cmd_args,
        workdir=workdir,
        design_dir=design_dir,
        slurm_options=slurm_params,
    )

    if cmd_args.cmd_mode == "local":
        cmd_results = run_cmd_local(
            cmd_path=cmd_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout=env.config.timeout,
        )
    elif cmd_args.cmd_mode == "slurm":
        cmd_results = run_cmd_slurm(
            cmd_path=cmd_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout=env.config.timeout,
            max_retries=5,
        )
    else:
        raise ValueError(f"Invalid cmd_mode '{cmd_args.cmd_mode}'.")

    return cmd_results


def read_scorefile(scorefile_path: Path) -> list[ScoreDict]:
    if not scorefile_path.exists():
        raise FileNotFoundError(f"Score file not found at {scorefile_path}.")

    results = []
    with scorefile_path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON line in score file {scorefile_path}: {line}"
                ) from e

    if not results:
        raise ValueError(f"No valid score entries found in {scorefile_path}.")

    return results


def save_results(
    results: list[ScoreDict] = None,
    workdir: Path = None,
    step: int = None,
    suffix: str | None = None,
) -> None:
    suffix_str = f"_{suffix}" if suffix else ""
    scorefile_path = workdir / f"score_{step}{suffix_str}.json"
    with scorefile_path.open("w") as f:
        json.dump(results, f, indent=2)


def make_designs(
    env: RosettaEnvironment = None,
    results: list[ScoreDict] = None,
    design_dir: Path = None,
    delete_decoy: bool = None,
) -> list[RosettaDesign]:
    designs = []
    for result in results:
        decoy = result.get("decoy", None)
        if decoy is None:
            raise ValueError(f"Missing 'decoy' key in score result: {result}")

        decoy_path = design_dir / f"{decoy}.pdb"
        parent_idx = int(decoy.split("_")[1])
        parent_path = env.state.designs[parent_idx].pdb

        if delete_decoy:
            try:
                decoy_path.unlink()
                decoy_path = parent_path
            except Exception as e:
                raise RuntimeError(f"Failed to remove decoy file {decoy_path}.") from e

        sequence = result.get("record_sequence", "").split(",")
        score_dict = {
            k: v for k, v in result.items() if k not in ["decoy", "record_sequence"]
        }
        designs.append(
            RosettaDesign(
                pdb=decoy_path,
                sequence=sequence,
                score_dict=score_dict,
                parent_pdb=parent_path,
            )
        )
    return designs


def run(
    env: RosettaEnvironment = None,
    act_name: RosettaAction = None,
    xml_args: dict = None,
    cmd_args: RosettaCmdArgs = None,
    workdir: Path = None,
    slurm_options: dict | None = None,
) -> RosettaActionResults:
    pareto_designs = [d for d in env.state.designs if d.is_pareto_efficient]
    if len(pareto_designs) == 0:
        raise RosettaActionError("No Pareto-efficient designs found in the state.")

    logger.info(f"Running action {act_name} on {len(pareto_designs)} design(s)")

    design_dir = workdir / "designs"
    design_dir.mkdir(parents=True, exist_ok=True)

    design_list_path = workdir / "designs.txt"
    with design_list_path.open("w") as f:
        for i, design in enumerate(pareto_designs):
            design_path = design_dir / f"design_{i}.pdb"
            shutil.copy(design.pdb, design_path)
            f.write(f"{design_path}\n")

    logger.info("Preparing action protocol...")
    xml_path = prepare_xml(
        env=env,
        act_name=act_name,
        xml_args=xml_args,
        workdir=workdir,
        suffix=cmd_args.suffix,
    )

    logger.info("Validating action protocol...")
    val_status_code, val_stderr = validate_cmd(
        env=env,
        xml_path=xml_path,
        design_list_path=design_list_path,
        cmd_args=cmd_args,
        workdir=workdir,
        design_dir=design_dir,
    )
    if val_status_code != "success":
        logger.error("Validation failed")
        return RosettaActionResults(status_code="validation_error", stderr=val_stderr)
    logger.info("Validation succeeded")

    logger.info("Running action protocol...")
    status_code, stderr = run_cmd(
        env=env,
        xml_path=xml_path,
        design_list_path=design_list_path,
        cmd_args=cmd_args,
        workdir=workdir,
        design_dir=design_dir,
        slurm_params=slurm_options,
    )
    if status_code != "success":
        logger.error(f"Command execution failed with exit code {status_code}")
        return RosettaActionResults(status_code=status_code, stderr=stderr)
    logger.info("Command execution succeeded")

    logger.info("Processing results...")
    scorefile_path = workdir / "score_out.sc"
    results = read_scorefile(scorefile_path)
    logger.info(f"Read {len(results)} score entries from {scorefile_path}")
    save_results(
        results=results,
        workdir=workdir,
        step=env.state.global_step + 1,
        suffix=cmd_args.suffix,
    )
    scorefile_path.unlink()

    logger.info("Making new designs...")
    designs = make_designs(
        env=env,
        results=results,
        design_dir=design_dir,
        delete_decoy=cmd_args.delete_decoy,
    )
    return RosettaActionResults(status_code=status_code, stderr=stderr, designs=designs)
