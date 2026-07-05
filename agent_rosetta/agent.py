from __future__ import annotations

import time
from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from .typing import StopStep, TrajectoryStep
from .utils.logging import console, logger

if TYPE_CHECKING:
    from .history import History
    from .trajectory import Trajectory
    from .typing import EnvironmentT, ModelT, ParserT, TaskT


class Agent:
    def __init__(self, model: ModelT = None, parser: ParserT = None):
        self.model = model
        self.parser = parser

        self.history: History = None

    def setup(self, env: EnvironmentT = None, task: TaskT = None):
        self.model.setup()
        self.parser.setup(env=env, task=task)
        self.history = task.build_history(env=env, agent=self)

        logger.info(f"System prompt:\n{self.history[0].content}")

    def run_step(
        self,
        task: TaskT = None,
        env: EnvironmentT = None,
        traj: Trajectory | None = None,
    ) -> TrajectoryStep:
        if len(self.history) >= 3 and self.history[-1].role == "assistant":
            last_message = task.build_next_step_message(env=env, agent=self, traj=traj)
            self.history.append(last_message)
        last_message = self.history[-1]

        console.print(
            Panel(
                Text(last_message.content),
                title="User",
                style="grey37",
                border_style="blue",
            )
        )
        logger.info(f"User message:\n{last_message.content}")

        parse_retries = 0
        while parse_retries <= self.parser.config.max_parse_retries:
            query_retries = 0
            while query_retries <= self.model.config.max_query_retries:
                with console.status(
                    Text("Thinking...", style="grey37"),
                    spinner="arc",
                    spinner_style="grey37",
                    refresh_per_second=4,
                ):
                    query_results = self.model.query(self.history)

                    reasoning = query_results.reasoning
                    content = query_results.content

                if query_results.finish_reason == "stop" and len(content) > 0:
                    self.history.add(
                        role="assistant", reasoning=reasoning, content=content
                    )

                    console.print(
                        Panel(
                            Text(reasoning),
                            title="Agent Rosetta (reasoning)",
                            style="grey37",
                            border_style="grey37",
                        )
                    )
                    console.print(
                        Panel(
                            Markdown(f"```xml\n{content}\n```"),
                            title="Agent Rosetta (response)",
                            style="grey37",
                            border_style="purple",
                        )
                    )
                    break

                time.sleep(10)
                query_retries += 1
                if query_retries == self.model.config.max_query_retries:
                    return StopStep()

            try:
                parser_output = self.parser.parse(content)
                break
            except Exception as e:
                logger.error(f"Parsing error:\n{e}")
                self.history.add(
                    role="user",
                    content=self.parser.config.parsing_error_template.format(
                        error=str(e)
                    ),
                )
                parse_retries += 1
                if parse_retries == self.parser.config.max_parse_retries:
                    console.print(
                        "Reached maximum number of parse retries, terminating run",
                        style="grey37",
                    )
                    logger.error(
                        "Reached maximum number of parse retries, terminating run"
                    )
                    return StopStep()

        try:
            start_time = time.time()
            state = env.get_state()
            observation = env.step(
                act_name=parser_output.act_name,
                act_args=parser_output.act_args,
                act_tag=parser_output.act_tag,
                task=task,
                traj=traj,
            )
            end_time = time.time()
        except Exception as e:
            logger.error(f"Environment step error:\n{e}")
            return StopStep()

        return TrajectoryStep(
            state=state,
            message=last_message,
            query_results=query_results,
            parser_output=parser_output,
            observation=observation,
            execution_time=end_time - start_time,
        )
