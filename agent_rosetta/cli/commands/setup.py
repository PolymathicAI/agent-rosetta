from __future__ import annotations

import json
import time

import click
import questionary
from questionary import Choice

from agent_rosetta.cli.constants import SUPPORTED_MODELS
from agent_rosetta.cli.logging import log_error, log_info, log_success, log_warning
from agent_rosetta.cli.typing import LLMProvider

from .common import get_config_dir


def setup():
    log_info("Setting up Agent Rosetta...")
    log_info()

    config_dir = get_config_dir()

    ### API keys ###
    provider_choices = [
        Choice(title=provider.value.name, value=provider)
        for provider in SUPPORTED_MODELS.keys()
    ]

    log_info("Please choose a LiteLLM provider:")
    provider: LLMProvider = questionary.select(
        "", choices=provider_choices, qmark="", pointer=">"
    ).ask()

    if provider == LLMProvider.OTHER:
        while True:
            provider_name = click.prompt(
                "Please enter the name of your LiteLLM provider (see https://docs.litellm.ai/docs/providers for a list of supported providers)"
            ).strip()
            if provider_name:
                break
            log_error("Provider name cannot be empty. Please try again.")
            time.sleep(1)

        api_key_env_var = click.prompt(
            "Please enter the name of the environment variable for the API key"
        )
    else:
        provider_name = provider.value.name
        api_key_env_var = provider.value.api_key_env_var

    api_key = click.prompt(
        f"Please enter your {provider_name} API key (input will be hidden)",
        default=api_key_env_var,
        hide_input=True,
    )

    ### Model selection ###
    model_choices: list[str] = SUPPORTED_MODELS[provider] + ["other"]

    while True:
        log_info("Please choose a model for your provider:")
        model = questionary.select(
            "", choices=model_choices, qmark="", pointer=">"
        ).ask()
        if model == "other":
            log_warning(
                "You chose to use a custom model. Please ensure its config file exists in `configs/model`, it is properly configured, and compatible with your provider."
            )
            time.sleep(1)
            confirmed = click.confirm(
                "Do you want to continue with a custom model?", default=True
            )
            if confirmed:
                while True:
                    model = click.prompt(
                        "Please enter the name of your custom model config file"
                    ).strip()
                    if model:
                        break
                    log_error(
                        "Model config file name cannot be empty. Please try again."
                    )
                    time.sleep(1)
                break
        else:
            break

    config: dict[str, str] = {}
    config["llm_providers"] = {provider_name: {api_key_env_var: api_key}}
    config["default_model"] = model

    config_path = config_dir / "config.json"

    if config_path.exists():
        with config_path.open("r") as f:
            existing_config: dict[str, str] = json.load(f)
        existing_config["llm_providers"].update(config["llm_providers"])
        existing_config["default_model"] = config["default_model"]
        config = existing_config

    try:
        with config_path.open("w") as f:
            json.dump(config, f, indent=4)
        log_success(f"Configuration saved successfully to '{config_path}'")
    except Exception as e:
        log_error(f"Failed to save configuration file to '{config_path}': {e}")
        raise click.Abort()
