from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from environments.rosetta.actions import BackboneChangeArgs


def prepare_movemap_factory(act_args: BackboneChangeArgs) -> str:
    template = """
        <MoveMapFactory name="map_factory" chi="true" bb="true">
            <Backbone residue_selector="{selector_name}"/>
        </MoveMapFactory>
    """

    if act_args.mover_name != "backrub":
        return ""

    if not act_args.mover_selector_name:
        return ""

    return template.format(selector_name=act_args.mover_selector_name).strip()


def prepare_mover(act_args: BackboneChangeArgs) -> str:
    mover_template = """<{mover_name} name="backbone_change" {mover_params} />"""

    mover_params = act_args.mover_params
    if act_args.mover_name == "backrub":
        if act_args.mover_selector_name:
            mover_params += ' movemap_factory="map_factory"'
    else:
        mover_params += ' scorefxn="scoring_post"'
        if act_args.mover_selector_name:
            mover_params += f' residue_selector="{act_args.mover_selector_name}"'

    return mover_template.format(
        mover_name=act_args.mover_name.capitalize(), mover_params=mover_params
    ).strip()
