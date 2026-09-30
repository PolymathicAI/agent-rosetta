# Agent guide

Agent Rosetta runs an LLM-driven refinement loop for protein-design tasks using
RosettaScripts. Use this guide when helping a user install the project, configure
and run a task, inspect results, or extend the implementation.

## Start here

- Read `README.md` and the relevant task and environment configuration before
  making changes. Use the implementation and `agr --help` to resolve discrepancies.
- Work from the repository root. Runtime code locates assets through the Git root,
  and example configurations use relative paths. Use an editable checkout; the
  wheel includes only `agent_rosetta`, not the task modules and runtime assets.
- Inspect `git status` and preserve existing user changes and run artifacts.
- Prefer a new task configuration over changing shared defaults for one experiment.
  Keep the user's design brief, input structure, and evaluation criteria explicit.

## Installation and configuration

The project uses `uv` and Python >=3.11.11; `.python-version` pins 3.11.11.
The documented CLI installation is:

```bash
uv tool install -e .
agr setup
agr setup-rosetta
```

Both setup commands are interactive. `agr setup` configures the LLM provider and
default model; `agr setup-rosetta` records paths to existing threaded and MPI
RosettaScripts executables. It does not install Rosetta.

Configuration is stored in
`${XDG_CONFIG_HOME:-~/.config}/agent-rosetta/config.json`, including API keys.
Do not print credentials or commit them. Reuse existing configuration when present;
let the user supply missing secrets through the interactive setup.

For development in a project environment:

```bash
uv sync --group dev --group test
uv run agr --help
```

Use `uv run agr` in place of `agr` for that environment. Dependencies include
PyTorch and Transformers; installation may require substantial downloads.

## Running and adapting tasks

```bash
agr run configs/hello-rosetta.yaml
agr run configs/pack-ncaa-local.yaml
agr run configs/fixed-backbone-sequence-design-slurm.yaml --output-dir ./outputs
```

- `hello-rosetta.yaml` is a one-step LLM connectivity/capabilities check. It calls
  the configured provider and is not an offline test or a Rosetta execution test.
- `pack-ncaa-{local,slurm}.yaml` packs TRF, a non-canonical amino acid, into a
  protein core. This task does not require ESMFold or a GPU.
- `fixed-backbone-sequence-design-{local,slurm}.yaml` designs canonical sequences
  and evaluates folds with ESMFold. The current implementation uses `cuda:0` and
  loads `facebook/esmfold_v1`, downloading model files if needed.

Top-level YAML files compose Hydra groups in `configs/{environment,model,task,parser,runner}`.
Copy a suitable top-level file within `configs/`, give it a distinct `name`, and
override nested settings there. Preserve its `defaults` list and `_self_` entry.
For example, these overrides can reduce a copied local task's workload:

```yaml
runner:
  config:
    max_steps: 2
task:
  config:
    initial_pdb: /absolute/path/to/input.pdb
    nstruct: 2
```

`agr run` accepts a configuration path and `--output-dir`; it does not expose
Hydra-style CLI overrides such as `task.config.nstruct=2`. Select a model through
the YAML `defaults` list or the saved default, using an existing file in
`configs/model/` as a template for new model configurations.

Before executing a protein-design run:

- Check the input PDB, task prompt, model/provider configuration, and Rosetta
  executable paths. Set `task.config.initial_pdb` explicitly for custom inputs;
  the example PDB interpolations should not be assumed to honor `AGR_PDB_DIR`.
- Match resources to the requested run. The supplied design tasks use
  `nstruct: 128`; MPI launches `nstruct + 2` processes, or 130 at that setting.
  The default refinement limit is 20 steps. Use a smaller configuration for a
  smoke run, and report that it differs from the full experiment.
- For SLURM, set `AGR_SLURM_PARTITION` in the repository's `.env` or process
  environment and inspect `task.config.slurm_options` for the target cluster.
- Inspect `environments/rosetta/scripts/cmd.sh`. Both local and SLURM execution
  use this template, which contains site-specific `module` commands. Adapt those
  commands to the host's installed Rosetta/MPI environment before running.
- Keep execution within the user's requested compute and API budget. A request
  to edit code or configuration alone is not a request to launch an experiment.

The CLI loads saved configuration before loading the repository `.env`.
Saved provider keys, model choice, and executable paths can therefore take
precedence over environment settings; inspect the loading code when diagnosing
configuration problems, without exposing secret values.

## Outputs and diagnosis

Runs write to
`<output-dir>/<sanitized-config-name>/<sanitized-model-choice>/<timestamp>/`.
The output root defaults to `outputs/`, can be set with `AGR_OUTPUT_DIR`, and can
be overridden with `--output-dir`.

Start diagnosis with `logs/main.log` and the relevant `step_*` directory's
generated XML, command scripts, and process logs. Completed runs save
`trajectory.json`; Rosetta runs also retain the initial PDB, timing information,
and per-step designs. Preserve failed-run artifacts for diagnosis.

When reporting a run, include the configuration, input structure, output path,
completion status, and relevant metrics. Distinguish measured results from
predictions: Rosetta energies, RMSD, and ESMFold confidence are computational
proxies, not experimental confirmation of stability or function.

## Where to make changes

| Path | Responsibility |
| --- | --- |
| `agent_rosetta/` | Agent loop, model interface, trajectory, base classes, and CLI |
| `configs/` | Hydra composition, model settings, prompts, and task parameters |
| `tasks/rosetta/` | Task setup, metrics, ensemble summaries, and feedback |
| `environments/rosetta/` | Rosetta actions, state, execution, XML templates, and tools |
| `environments/rosetta/docs/` | Action documentation shown to the runtime LLM |
| `environments/rosetta/ncaas/` | Rosetta residue parameter files |
| `parsers/rosetta/` | Action XML parsing, schema, and composition-penalty syntax |
| `runners/refine.py` | Refinement loop and stopping behavior |
| `assets/pdbs/` | Example input structures |

When adding or changing an action, keep its argument types, parser/schema,
execution implementation, XML templates, and LLM-facing documentation consistent.
When adding a task, follow the existing task subclass and Hydra `_target_`
patterns. Keep scientific objectives and metric definitions consistent with the
task prompt; do not silently change them to improve reported results.

## Code style and validation

Follow `pyproject.toml`: Ruff targets Python 3.11 with an 88-character line length,
sorted imports, pathlib usage, no parent-relative imports, and no `typing.Any`.
Follow existing typing and dataclass/Pydantic conventions. Change dependencies
in `pyproject.toml` and update `uv.lock` through `uv`; do not hand-edit the lockfile.

For changed Python files, run the relevant checks, substituting their paths:

```bash
uv run ruff check path/to/changed_file.py
uv run ruff format --check path/to/changed_file.py
```

Test behavior at the affected layer without launching a full design run by
default. Check configuration composition separately from runtime instantiation,
which can initialize external tools. Run Rosetta or API-dependent checks when
the required tools, credentials, and execution scope are available.

The configured pytest path, `environments/rosetta/tests`, is ignored by Git and
absent from the tracked checkout. `parsers/rosetta/test_parser.py` is a manual
Hydra demonstration that catches and prints errors, not a reliable pytest suite.
Do not claim tests pass based on an empty collection or this script's exit code.
For code changes, add focused regression coverage where practical and report
exactly which checks ran, along with any unverified behavior.
