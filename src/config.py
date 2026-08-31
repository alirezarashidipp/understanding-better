import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr


class AppSettings(BaseModel):
    root: Path
    openai_api_key: SecretStr
    openai_model: str
    openai_temperature: float

    @classmethod
    def from_env(cls, root: Path | None = None) -> "AppSettings":
        project_root = (root or Path.cwd()).resolve()
        load_dotenv(project_root / ".env.local")

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        temperature_text = os.getenv("OPENAI_TEMPERATURE", "0.0").strip()
        if not api_key or not model:
            raise RuntimeError(
                "OPENAI_API_KEY and OPENAI_MODEL must be set in the environment or .env.local."
            )

        try:
            temperature = float(temperature_text)
        except ValueError:
            raise RuntimeError("OPENAI_TEMPERATURE must be a number from 0.0 to 2.0.") from None
        if not 0.0 <= temperature <= 2.0:
            raise RuntimeError("OPENAI_TEMPERATURE must be from 0.0 to 2.0.")

        return cls(
            root=project_root,
            openai_api_key=SecretStr(api_key),
            openai_model=model,
            openai_temperature=temperature,
        )
