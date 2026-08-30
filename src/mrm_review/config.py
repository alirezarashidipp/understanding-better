import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr


class AppSettings(BaseModel):
    root: Path
    openai_api_key: SecretStr
    openai_model: str

    @classmethod
    def from_env(cls, root: Path | None = None) -> "AppSettings":
        project_root = (root or Path.cwd()).resolve()
        load_dotenv(project_root / ".env.local")

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        if not api_key or not model:
            raise RuntimeError(
                "OPENAI_API_KEY and OPENAI_MODEL must be set in the environment or .env.local."
            )

        return cls(
            root=project_root,
            openai_api_key=SecretStr(api_key),
            openai_model=model,
        )
