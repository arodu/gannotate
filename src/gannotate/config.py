"""Configuration handling for Gannotate."""

import json
import os

APP_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "gannotate",
)
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

DEFAULT_CONFIG = {
    # Empty by default: uploads are opt-in. Use %f for the file path.
    "upload_command": "",
    "default_color": [0.95, 0.15, 0.15],
    "default_width": 4,
    "arrow_style": "classic",
}


def load_config():
    config = DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            config.update(data)
    except (OSError, ValueError):
        pass
    return config


def save_config(config):
    os.makedirs(APP_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, sort_keys=True)
        fh.write("\n")
