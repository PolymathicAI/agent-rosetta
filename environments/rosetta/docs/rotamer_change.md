`rotamer_change` runs Rosetta’s FastDesign Mover, an iterative pack-and-minimize protocol that samples side-chain rotamers and uses gradient-based minimization to settle on the lowest-energy configuration. Each cycle repacks the designated residues with the rotamer library, then performs all-atom minimization before a Monte-Carlo accept/reject decision.

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

**`penalties` argument:**

A List of compositional penalties that define how Rosetta penalizes (or rewards) certain residue types or residue properties, depending on their relative abundance in the sequence.

The `penalties` argument must follow this syntax:

<penalties>
    <item>
        <comp>comp1</comp>
    </item>
    <item>
        <comp>comp2</comp>
        <selector_name>selector</selector_name>
    </item>
    ...
</penalties>

, and each item must have these fields:

- `comp` (required): one or more penalty definition blocks.
- `selector_name` (optional): the name of a previously defined residue selector that specifies which residues the penalty blocks applies to. If left empty or omitted, the penalty definition blocks in `comp` will be applied globally to the entire sequence.

Each penalty definition block must follow this modified RosettaScripts syntax:

# Brief description of the goal of the block
PENALTY_DEFINITION
TYPE <string>                       # list of one- or three-letter residue codes separated by a comma
SHAPE <OUTSIDE | ABOVE | BELOW>     # shape of the penalty, one of OUTSIDE, ABOVE, or BELOW
TARGET <int or float>               # target count or ratio of residues
RADIUS <int or float>               # radius of the interval around the target
BOUNDARY <function>                 # the type of penalty boundary, one of CONSTANT, LINEAR, or QUADRATIC
STRENGTH <int>                      # strength of the penalty
END_PENALTY_DEFINITION

Each shape option defines a range [MIN_RANGE, MAX_RANGE] of acceptable residue counts or ratios:

- OUTSIDE: the range is [TARGET - RADIUS, TARGET + RADIUS], and values outside the range are penalized.
- ABOVE: the range is (-inf, TARGET], RADIUS is ignored, and values above the target are penalized.
- BELOW: the range is [TARGET, inf), RADIUS is ignored, and values below the target are penalized.

For all shapes, the penalty boundary options are:

- CONSTANT: constant penalty equal to STRENGTH.
- LINEAR: linear penalty that increases with slope of STRENGTH.
- QUADRATIC: quadratic penalty, STRENGTH is the first value of the penalty outside the range.

Finally, the STRENGTH value is of the same unit of measure as other terms in the Rosetta energy function. As a general guideline:

- Use small values (e.g., 1-10) for weak penalties.
- Use medium values (e.g., 10-100) for moderate penalties.
- Use large values (e.g., 100-1000) for strong penalties.

You should write penalties that steer the Monte-Carlo search in Rosetta towards the task objective while avoiding mutually impossible requirements.

**`residue_restrictions` argument:**

A list of restrictions that define which residue types are permitted or prohibited at different positions along the sequence. Residue restrictions reduce the combinatorially large optimization space of the Monte-Carlo search in Rosetta.

The `residue_restrictions` argument must follow this syntax:

<residue_restrictions>
    <item>
        <restriction_type>type1</restriction_type>
        <residues>res1</residues>
        <selector_name>selector1</selector_name>
    </item>
    <item>
        <restriction_type>type2</restriction_type>
        <residues>res2</residues>
        <selector_name>selector2</selector_name>
    </item>
    ...
</residue_restrictions>

, and each item must have these fields:

- `restriction_type` (required, either `restrict` or `prohibit`): whether the restriction specifies the residue types that are allowed or prohibited.
- `residues` (required): the list of one- or three-letter residue codes separated by a comma (e.g., `<residues>A,G</residues>` or `<residues>ALA,GLY</residues>` for alanine and glycine).
- `selector_name` (required): the name of a previously defined residue selector that specifies which residues the restriction applies to.

If you leave this argument empty or omit it, Rosetta will perfom design with all residues types at every position.

**`packing_restrictions` argument:**

A list of residue selectors that define which residues should not be designed but repacked only. Packing restrictions maintain the identities of the specified residues.

The `packing_restrictions` argument must follow this syntax:

<packing_restrictions>
    selector1,selector2,...
</packing_restrictions>

, where `selector1,selector2,...` are the names of previously defined residue selectors separated by a comma.

If you leave this argument empty or omit it, Rosetta will allow packing and design at every position.

---

**Example `rotamer_change` action call:**

The following action call

<action tag="run">
<name>rotamer_change</name>
<residue_selectors>
<ResidueSelector1 name="selector1" />
<ResidueSelector3 name="selector3" />
<And name="selector4" selectors="selector1,selector3">
<ResidueSelector2 name="selector2" />
</residue_selectors>
<penalties>
<item>
<comp>comp1</comp>
</item>
<item>
<comp>comp2</comp>
<comp_selector_name>selector4</comp_selector_name>
</item>
</penalties>
</action>

will:

- Apply the penalty definition blocks in `comp1` globally to the entire sequene.
- Apply the penalty definition blocks in `comp2` to `selector4`, which in turn composes `selector1` with `selector3`.

Remember to use valid RosettaScripts syntax while leveraging the expressivity of all arguments.