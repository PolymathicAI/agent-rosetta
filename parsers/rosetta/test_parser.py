from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import hydra
from hydra.utils import instantiate

from agent_rosetta.utils.fs import get_root_dir

if TYPE_CHECKING:
    from omegaconf import DictConfig

    from .parser import RosettaParser


root_dir = get_root_dir()

test_actions = [
    dedent("""
<action tag="run">
<name>rotamer_change</name>
<penalties>
<item>
<comp># Favor ~50% hydrophobic residues
PENALTY_DEFINITION
TYPE A,V,I,L,F,W,Y,M
ABSOLUTE 46
DELTA_START -10
DELTA_END 10
PENALTIES 5.0 4.5 4.0 3.5 3.0 2.5 2.0 1.5 1.0 0.5 0.0 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0 4.5 5.0
BEFORE_FUNCTION QUADRATIC
AFTER_FUNCTION QUADRATIC
END_PENALTY_DEFINITION</comp>
</item>
</penalties>
</action>
        """),
    dedent("""
<action tag="run">
<name>rotamer_change</name>
<penalties>
<item>
<comp>
# Encourage natural hydrophobic content (~30%)
PENALTY_DEFINITION
TYPE L,I,V,F,W,M,A
FRACTION 0.30
FRACT_DELTA_START -0.10
FRACT_DELTA_END 0.10
PENALTIES 5.0 3.0 1.0 0.0 1.0 3.0 5.0
BEFORE_FUNCTION QUADRATIC
AFTER_FUNCTION QUADRATIC
END_PENALTY_DEFINITION

# Penalize high glycine content
PENALTY_DEFINITION
TYPE G
FRACTION 0.10
FRACT_DELTA_START 0.00
FRACT_DELTA_END 0.10
PENALTIES 0.0 5.0
BEFORE_FUNCTION LINEAR
AFTER_FUNCTION QUADRATIC
END_PENALTY_DEFINITION
</comp>
</item>
</penalties>
</action>
        """),
]

test_simple_actions = [
    dedent("""
<action tag="run">
<name>rotamer_change</name>
<penalties>
<item>
<comp>
PENALTY_DEFINITION
TYPE GLY
SHAPE ABOVE
TARGET 0.3
RADIUS 0.1
BOUNDARY LINEAR
STRENGTH 100
END_PENALTY_DEFINITION
</comp>
</item>
</penalties>
</action>
""")
]


def test_parser(config):
    config.config.simple_aacomp_syntax = False
    parser: RosettaParser = instantiate(config)

    for content in test_actions:
        print(f"### Testing parser with content:{content}")
        try:
            act_tag, act_name, act_params = parser.parse(content)
            print("Results:")
            print(f"Action tag: {act_tag}")
            print(f"Action name: {act_name}")
            print(f"Action params: {act_params}")
            print()
        except Exception as e:
            print(f"Error occurred while parsing content: {e}")


def test_simple_parser(config):
    config.config.simple_aacomp_syntax = True
    simple_parser: RosettaParser = instantiate(config)

    for content in test_simple_actions:
        print(f"### Testing simple parser with content:{content}")
        try:
            act_tag, act_name, act_params = simple_parser.parse(content)
            print("Results:")
            print(f"Action tag: {act_tag}")
            print(f"Action name: {act_name}")
            print(f"Action params: {act_params}")
            print()
        except Exception as e:
            print(f"Error occurred while parsing content: {e}")


@hydra.main(
    version_base=None,
    config_path=root_dir / "configs" / "parser",
    config_name="rosetta",
)
def main(parser_config: DictConfig):
    test_parser(parser_config)
    test_simple_parser(parser_config)


if __name__ == "__main__":
    main()
