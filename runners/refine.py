from __future__ import annotations

from agent_rosetta.runner import Runner, RunnerConfig
from agent_rosetta.typing import StopStep
from agent_rosetta.utils.logging import console, logger


class RefineRunner(Runner[RunnerConfig]):
    def __init__(self, config: RunnerConfig):
        super().__init__(config)

    def run(self):
        while self.env.state.global_step < self.config.max_steps:
            step_number = self.env.state.global_step + 1

            console.print(
                f"Running step {step_number}/{self.config.max_steps}",
                style="grey37",
            )
            logger.info(f"Running step {step_number}/{self.config.max_steps}")

            step = self.agent.run_step(
                task=self.task, env=self.env, traj=self.trajectory
            )
            self.trajectory.add(step)

            if isinstance(step, StopStep):
                console.print(
                    ":heavy_exclamation_mark: Stop signal received, terminating run",
                    style="grey37",
                )
                logger.error("StopStep received, terminating run")
                break
            console.print(
                f":heavy_check_mark: Step {step_number} completed",
                style="grey37",
            )
            logger.info(f"Step {step_number} completed")

        console.print("Run complete", style="grey37")
        logger.info("Run complete")
