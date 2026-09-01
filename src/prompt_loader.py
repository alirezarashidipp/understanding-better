from pathlib import Path

import yaml

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Prompt file {filename} must contain a YAML mapping.")

    instructions = data.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(f"Prompt file {filename} requires instructions.")
    return instructions.strip()
