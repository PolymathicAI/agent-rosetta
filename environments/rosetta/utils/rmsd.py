from __future__ import annotations

from typing import TYPE_CHECKING

import biotite.structure as struc
from biotite.structure import superimpose
from biotite.structure.io.pdb import PDBFile

if TYPE_CHECKING:
    from pathlib import Path

    from biotite.structure.atoms import AtomArray, AtomArrayStack


def pdb_to_array(pdb_path: Path) -> AtomArray | AtomArrayStack:
    pdb = PDBFile.read(pdb_path)
    array: AtomArray | AtomArrayStack = (
        pdb.get_structure(model=1) if pdb.get_model_count() else pdb.get_structure()
    )
    return array


def measure_rmsd(a: Path, b: Path) -> float:
    struct_a = pdb_to_array(a)
    struct_b = pdb_to_array(b)

    mask_sel = "CA"
    mask_a = struct_a.atom_name == mask_sel
    mask_b = struct_b.atom_name == mask_sel

    sel_a = struct_a[mask_a]
    sel_b = struct_b[mask_b]

    fitted_b, _ = superimpose(sel_a, sel_b)
    return struc.rmsd(sel_a, fitted_b).item()
