"""
JSON/YAML read-write helpers and configuration loader.

All file I/O for the pipeline goes through these functions to ensure
consistent encoding, directory creation, and .env loading.
"""

import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_json(path: str) -> list | dict:
    """Load and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON data (list or dict).

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: str) -> None:
    """Save data to a JSON file with proper Unicode support.

    Creates parent directories if they don't exist.

    Args:
        data: Data to serialize (must be JSON-serializable).
        path: Destination file path.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config(path: str = "config/settings.yaml") -> dict:
    """Load pipeline configuration from YAML and environment variables.

    Loads .env file (if present) into environment variables via python-dotenv,
    then parses and returns the YAML configuration.

    Args:
        path: Path to the YAML config file.

    Returns:
        Configuration dictionary with all pipeline settings.
    """
    load_dotenv()
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(path: str) -> str:
    """Load a prompt template from a text file.

    Args:
        path: Path to the prompt file.

    Returns:
        The prompt text as a string.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
