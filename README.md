<p align="center">
    <img src="./assets/agent_rosetta_color_white_bg.svg" width="40%">
</p>
<p align="center" width="100%">
    <a href="https://arxiv.org/pdf/2603.15952">paper</a> | 
    <a href="https://polymathic-ai.org/blog/agent-rosetta/">blog</a>
</p>

An LLM agent to execute protein-design tasks with [RosettaScripts](https://docs.rosettacommons.org/docs/latest/scripting_documentation/RosettaScripts/RosettaScripts).

# Installation

To install Agent Rosetta's `agr` command-line interface, run:

```bash
> uv tool install -e .
> agr setup     # Specify API keys
```

# Hello, Rosetta!

To verify Agent Rosetta is correctly installed, run:

```bash
> agr run configs/hello-rosetta.yaml
```

This task will instruct Agent Rosetta to explain its capabilities:

![A GIF of the terminal](./assets/vhs/output/hello-rosetta.gif)

# Running Protein-design Tasks

First, setup the paths to the `cxx11` and `mpi` version of RosettaScripts ([RosettaScripts build instructions](https://docs.rosettacommons.org/docs/latest/build_documentation/Build-Documentation)):

```bash
> agr setup rosetta
```

This repo contains configuration files for the tasks presented in our paper:

* `configs/fixed-backbone-sequence-designs-{local/slurm}.yaml` for fixed backbone sequence design with canonical amino acids only (requires a GPU to run ESMFold).
* `configs/pack-ncaa-{local/slurm}.yaml` for packing TRF in the core of a protein (does not require a GPU).

Both tasks use the `mpi` version of RosettaScripts to generate ensembles of 128 candidate designs at each step:

* The `-local` configs run RosettaScripts locally. Make sure the host machine has at least 130 processes available for MPI.
* The `-slurm` configs run RosettaScripts as SLURM jobs. Write your `AGR_SLURM_PARTITION` environment variable in a `.env` file.

Then, for example, run:

```bash
> agr run configs/pack-ncaa-slurm.yaml
```

# Links

- Paper: [arXiv:2603.15952](https://arxiv.org/pdf/2603.15952)
- Blog: [Polymathic AI website](https://polymathic-ai.org/blog/agent-rosetta/)

# Citation

If you find this project useful, please cite:

```bibtex
@article{teneggi2026protein,
  title={Protein Design with Agent Rosetta: A Case Study for Specialized Scientific Agents},
  author={Teneggi, Jacopo and Turzo, SM and Marwah, Tanya and Bietti, Alberto and Renfrew, P Douglas and Mulligan, Vikram Khipple and Golkar, Siavash},
  journal={arXiv preprint arXiv:2603.15952},
  year={2026}
}
```

# Acknowledgements

We thank Lucy Reading-Ikkanda and Aditya Chhatrala for their contribution to the artwork.

# License

This project is licensed under the [MIT License](LICENSE).
