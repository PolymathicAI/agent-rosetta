import os
from pathlib import Path

from .typing import LLMProvider, rosettascripts_mode

APP_NAME: str = "agent-rosetta"
AGR_CONFIG_DIR: Path = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    / APP_NAME
)
AGR_OUTPUT_DIR: Path = Path(
    os.environ.get("AGR_OUTPUT_DIR", Path.cwd() / "outputs")
).expanduser()
AGR_PDB_DIR: Path = Path(
    os.environ.get("AGR_PDB_DIR", Path.cwd() / "assets" / "pdbs")
).expanduser()

ROSETTASCRIPTS_BINARIES: dict[rosettascripts_mode, str] = {
    "cxx11thread": "rosetta_scripts.cxx11thread.linuxgccrelease",
    "mpi": "rosetta_scripts.cxx11threadmpiserialization.linuxgccrelease",
}

SUPPORTED_MODELS: dict[LLMProvider, list[str]] = {
    LLMProvider.ANTHROPIC: ["ant-sonnet-4.6", "ant-opus-4.6"],
    LLMProvider.OPENAI: ["oai-gpt-5", "oai-gpt-5-mini"],
    LLMProvider.OPENROUTER: ["or-sonnet-4.5", "or-qwen3-235b", "or-gemini-2.5-flash"],
    LLMProvider.OTHER: [],
}
