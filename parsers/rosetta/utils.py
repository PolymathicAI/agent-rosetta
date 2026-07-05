from __future__ import annotations

from agent_rosetta.utils.logging import logger
from environments.rosetta.constants.aa import AA_1TO3


def normalize(restype: str) -> str:
    if len(restype) == 3:
        return restype

    normalized_restype = AA_1TO3.get(restype, "")
    if not normalized_restype:
        logger.warning(f"Unknown restype: {restype}, skipping")
    return normalized_restype


def normalize_restypes(restypes: str = None, separator: str = None) -> str:
    return separator.join(
        list(set(normalize(restype) for restype in restypes.upper().strip().split(",")))
    )
