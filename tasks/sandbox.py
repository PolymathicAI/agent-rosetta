from __future__ import annotations

from typing import TYPE_CHECKING

from agent_rosetta.history import History
from agent_rosetta.task import Task, TaskConfig
from environments.rosetta.actions import RosettaActions

if TYPE_CHECKING:
    from agent_rosetta.agent import Agent
    from agent_rosetta.typing import EnvironmentT


class SandboxTask(Task[TaskConfig]):
    def setup(self, *args, **kwargs):
        pass

    def build_history(self, env: EnvironmentT = None, agent: Agent = None) -> History:
        system_prompt = env.config.system_prompt
        task_prompt = self.config.prompt
        reasoning_formatting = agent.model.config.reasoning_formatting or ""

        messages = [
            {
                "role": "system",
                "content": system_prompt.format(
                    docs=RosettaActions.to_docs(),
                    reasoning_formatting=reasoning_formatting,
                ),
            },
            {"role": "user", "content": task_prompt.strip()},
        ]
        return History(messages)

    def build_next_step_message(self, *args, **kwargs):
        pass
