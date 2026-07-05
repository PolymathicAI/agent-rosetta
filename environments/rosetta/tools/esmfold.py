from __future__ import annotations

import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import TYPE_CHECKING

import torch
from transformers import AutoTokenizer
from transformers import EsmForProteinFolding as ESMFoldModel
from transformers.models.esm.openfold_utils.feats import atom14_to_atom37
from transformers.models.esm.openfold_utils.protein import Protein as OFProtein
from transformers.models.esm.openfold_utils.protein import to_pdb

from agent_rosetta.utils.logging import logger

if TYPE_CHECKING:
    from transformers.models.esm.modeling_esmfold import EsmForProteinFoldingOutput


def output_to_pdb(outputs: EsmForProteinFoldingOutput) -> list[str]:
    final_atom_positions = atom14_to_atom37(outputs["positions"][-1], outputs)
    outputs = {k: v.to("cpu").numpy() for k, v in outputs.items()}
    final_atom_positions = final_atom_positions.cpu().numpy()
    final_atom_mask = outputs["atom37_atom_exists"]

    pdbs = []
    for i in range(outputs["aatype"].shape[0]):
        aa = outputs["aatype"][i]
        pred_pos = final_atom_positions[i]
        mask = final_atom_mask[i]
        resid = outputs["residue_index"][i] + 1
        pred = OFProtein(
            aatype=aa,
            atom_positions=pred_pos,
            atom_mask=mask,
            residue_index=resid,
            b_factors=outputs["plddt"][i],
            chain_index=outputs["chain_index"][i] if "chain_index" in outputs else None,
        )
        pdbs.append(to_pdb(pred))
    return pdbs


def output_to_ca_plddt(outputs: EsmForProteinFoldingOutput) -> list[float]:
    return torch.mean(outputs["plddt"][..., 1], dim=-1).cpu().tolist()


class ESMFold:
    def __init__(self, device: str = "cuda:0", log_filename: str = None):
        log_file = Path(os.getenv("LOG_DIR")) / log_filename
        logger.add(
            log_file,
            level="DEBUG",
            enqueue=True,
            backtrace=True,
            diagnose=True,
            filter=lambda record: record["extra"].get("component") == "esmfold",
        )
        self.logger = logger.bind(component="esmfold")

        self.logger.info(f"========== Loading ESMFold on {device} ==========")
        with log_file.open("a") as f, redirect_stdout(f), redirect_stderr(f):
            self.model = ESMFoldModel.from_pretrained(
                "facebook/esmfold_v1", use_safetensors=True
            )
            self.tokenizer = AutoTokenizer.from_pretrained("facebook/esmfold_v1")
        self.logger.info("========== ESMFold loaded successfully ==========")

        self.model = self.model.to(device)
        self.device = device

    @torch.inference_mode()
    def predict(self, sequences: list[str]) -> EsmForProteinFoldingOutput:
        inputs = self.tokenizer(
            sequences, return_tensors="pt", add_special_tokens=False
        )
        inputs = inputs.to(self.device)
        return self.model(**inputs)

    def predict_pdb(
        self, sequences: list[str] = None, batch_size: int = None
    ) -> tuple[list[str], list[float]]:
        pdbs, ca_plddts = [], []

        batch_size = batch_size or len(sequences)
        batches = [
            sequences[i : i + batch_size] for i in range(0, len(sequences), batch_size)
        ]

        for batch in batches:
            batch_sequence_lines = "\n".join([f"> {seq}" for seq in batch])
            self.logger.info(
                f"ESMFold: Predicting PDB for sequences\n{batch_sequence_lines}"
            )

            batch_outputs = self.predict(batch)
            batch_pdbs = output_to_pdb(batch_outputs)
            batch_ca_plddts = output_to_ca_plddt(batch_outputs)

            pdbs.extend(batch_pdbs)
            ca_plddts.extend(batch_ca_plddts)
        return pdbs, ca_plddts
