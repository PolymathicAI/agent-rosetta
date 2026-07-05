from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, get_args

from pydantic import ValidationError

from agent_rosetta.parser import Parser, ParserConfig
from agent_rosetta.typing import ActionTag, ParserOutput
from environments.rosetta.actions import RosettaActions
from environments.rosetta.typing import RosettaAction

from .simple_aacomp import SimpleAACompBlock
from .utils import normalize_restypes

if TYPE_CHECKING:
    from environments.rosetta.environment import RosettaEnvironment


class RosettaParserConfig(ParserConfig):
    pass


class RosettaParser(Parser[ParserConfig]):
    list_fields: list[str] = {"penalties", "residue_restrictions"}

    def setup(self, **kwargs):
        pass

    def inner_xml_or_text(self, element: ET.Element) -> str:
        if len(element):
            return "\n".join(
                ET.tostring(c, encoding="unicode").strip() for c in element
            )
        return element.text.strip() if element.text else ""

    def parse_field(self, element: ET.Element) -> str | list[dict[str, str]]:
        if element.tag in RosettaParser.list_fields:
            return [
                {child.tag: self.inner_xml_or_text(child) for child in item}
                for item in element
            ]
        return self.inner_xml_or_text(element)

    def parse(
        self, content: str, env: RosettaEnvironment | None = None
    ) -> ParserOutput:
        root = ET.fromstring(f"<root>{content}</root>")

        action = root.find("action")
        if action is None:
            raise ValueError(f"No <action> element found in:\n{content}")

        act_name: RosettaAction = action.findtext("name", "").strip()
        if not act_name:
            raise ValueError(f"No <name> element found in <action>:\n{content}")
        if act_name not in get_args(RosettaAction):
            raise ValueError(f"Invalid action '{act_name}' in:\n{content}")
        act_name = act_name.strip()

        act_tag: ActionTag = action.get("tag", "").strip()
        if not act_tag:
            raise ValueError(f"No 'tag' attribute found in <action>:\n{content}")
        if act_tag not in get_args(ActionTag):
            raise ValueError(f"Invalid action tag '{act_tag}' in:\n{content}")

        if act_tag == "choose":
            return ParserOutput(act_name=act_name, act_tag=act_tag)

        act_args_dict = {
            child.tag: self.parse_field(child)
            for child in action
            if child.tag != "name"
        }

        try:
            RosettaActions.from_act_args_dict(
                act_name=act_name, act_args_dict=act_args_dict
            )
        except ValidationError as e:
            raise ValueError(
                f"Validation error for action '{act_name}'.\n\n"
                f"args:\n{act_args_dict}\n\n"
                f"error:\n{e}"
            )

        if "residue_restrictions" in act_args_dict:
            restrictions = act_args_dict["residue_restrictions"]
            for restriction in restrictions:
                residues = restriction.get("residues", "")
                residues = normalize_restypes(residues, separator=",")
                restriction["residues"] = residues

        if "penalties" in act_args_dict:
            block_pattern = (
                r"""PENALTY_DEFINITION\s*(?P<body>.*?)\s*END_PENALTY_DEFINITION"""
            )
            block_regex = re.compile(block_pattern, re.DOTALL | re.VERBOSE)

            penalties = act_args_dict["penalties"]
            for penalty in penalties:
                comp = penalty.get("comp", "")

                aacomps = []
                for block_match in block_regex.finditer(comp):
                    body = block_match.group("body").strip()
                    block = SimpleAACompBlock.from_body(body)
                    aacomps.append(block.to_aacomp_block())

                penalty["comp"] = "\n\n".join(aacomps)

        act_args = RosettaActions.from_act_args_dict(
            act_name=act_name, act_args_dict=act_args_dict
        )
        return ParserOutput(act_name=act_name, act_tag=act_tag, act_args=act_args)
