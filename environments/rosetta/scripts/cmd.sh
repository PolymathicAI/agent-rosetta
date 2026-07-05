#!/usr/bin/env bash
{slurm_flags}

set -euo pipefail

module --force purge
module load modules/2.4-20250724
module load slurm gcc/13.3.0 gdb git openmpi4 python3 qt/5.15.16 boost/1.87.0 jemalloc/5.3.0

{mpi_preamble}{exec_path} {validate_and_exit}\
    {input_pdb} \
    -in:file:fullatom \
    -parser:protocol {xml_path} \
    -out:path:pdb {output_dir_pdb} \
    -out:path:score {output_dir_score} \
    -out:no_nstruct_label \
    -out:suffix _out \
    -nstruct {nstruct} \
    -jd2:failed_job_exception {jd2_failed_job_exception} \
    -write_all_connect_info \
    -symmetric_gly_tables true \
    -scorefile_format json \
    {native_pdb} \
    {extra_res_fa}

rm -f ROSETTA_CRASH.log
