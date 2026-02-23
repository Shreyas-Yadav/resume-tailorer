"""Simplified configuration manager using JSON + env vars."""

import json
import os
from pathlib import Path
from typing import Any, Optional

CONFIG_FILE = Path.home() / ".resume-tailor" / "config.json"

DEFAULT_CONFIG = {
    "provider": "gemini",
    "model": None,
    "resume": None,
    "projects": "./projects.md",
    "output_dir": "./output",
}


def load_config() -> dict:
    """Load config from file, falling back to defaults."""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
    # Env vars override file config
    if env_provider := os.getenv("AI_PROVIDER"):
        config["provider"] = env_provider
    return config


def save_config(config: dict) -> None:
    """Persist config to disk."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_config_value(key: str) -> Any:
    """Get a single config value."""
    return load_config().get(key)


def set_config_value(key: str, value: Any) -> None:
    """Set a single config value and save."""
    config = load_config()
    config[key] = value
    save_config(config)
