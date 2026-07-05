from __future__ import annotations

from agent_rosetta.parser import Parser, ParserConfig
from agent_rosetta.typing import ParserOutput


class SandboxParser(Parser[ParserConfig]):
    def setup(self, **kwargs):
        pass

    def parse(self, content: str) -> ParserOutput:
        return ParserOutput(
            act_name="sandbox", act_tag="run", act_args_dict={"content": content}
        )
