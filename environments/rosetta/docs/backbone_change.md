`backbone_change` implements three different Rosetta backbone movers that perturb the backbone structures by random amounts, and then accept or reject perturbations with a Monte-Carlo test. They enable backbone wiggles, loop exploration, or gentle refinement between design steps. The supported backbone movers are: 

- `Small`: makes small-move-style torsion moves (no propagation minimization).
- `Shear`: makes shear-style torsion moves that minimize downstream propagation.
- `Backrub`: makes local rotations around two backbone atoms. 

**`mover_name` argument:**

The name of the Rosetta backbone mover to use.

**`mover_params` argument:**

The parameters of the Rosetta mover as XML flags. The allowed parameters for each mover are:

- For `Small`: `temperature`, `nmoves`, `angle_max`,
- For `Shear`: `temperature`, `nmoves`, `angle_max`,
- For `Backrub`: `pivot_residues`, `pivot_atoms`, `min_atoms`, `max_atoms`

**`residue_selectors` argument:**

ResidueSelectors are used to define logical selections of residues in a structure. They act as a flexible query language for picking out subsets of residues based on various criteria such as residue type, position, secondary structure, chain, neighborhood, and more.

Some example residue selectors are:

- Conformation independent residue selectors: `Index`, `Slice`, `ResidueName`, e.g.:

<Index name="string" resnums="string">
<ResidueName name="string" residue_names="string">

- Conformation dependent residue selectors: `Layer`, `Bonded`, `Neighborhood`, e.g.:

<Layer name="string" select_core="bool" select_boundary="bool" select_surface="bool">
<Neighborhood name="string" resnums="string" distance="float"/>

- Logical residue selectors: `And`, `Or`, `Not`, e.g.:

<And name="string" selectors="string">
<Not name="string" selector="string">

If no residue selectors are needed for the action, leave this argument empty or omit it.

**`mover_selector_name` argument:**

The name of a previously defined residue selector that specifies which residues the mover should be applied to. If you do not specify this argument, the mover will be applied to the entire sequence.

---

For example

<action tag="run">
<name>backbone_change</name>
<mover_name>mover</mover_name>
<mover_params>param1="value1" param2="value2"</mover_params>
<residue_selectors>
    <ResidueSelector1 name="selector1" />
    <ResidueSelector2 name="selector2" />
    <And name="selector3" selectors="selector1,selector2">
</residue_selectors>
<mover_selector_name>selector3</mover_selector_name>
</action>

will apply the mover to `selector3`, which in turn composes `selector1` with `selector2`.

Mover parameters and residue selectors are extremely powerful tools when combined together to achieve design goals.
So, be creative! Fully leverage their expressivity in your design protocol while using valid Rosetta syntax.