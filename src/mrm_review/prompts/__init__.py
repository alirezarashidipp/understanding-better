from pathlib import Path

import yaml

PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"Prompt file '{filename}' must contain a YAML mapping.")

    version = data.get("version")
    instructions = data.get("instructions")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"Prompt file '{filename}' must contain a version.")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(f"Prompt file '{filename}' must contain instructions.")

    return instructions.strip()
