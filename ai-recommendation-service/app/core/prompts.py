from pathlib import Path

from app.core.config import settings

DEFAULT_SYSTEM_PROMPT = (
    "Tu es un consultant senior en maturité des données NDI. "
    "Tu calcules le Best Path à partir de domainsSummary."
)


def get_system_prompt_path() -> Path:
    return settings.SYSTEM_PROMPT_PATH


def load_system_prompt(path: Path | None = None) -> str:
    prompt_path = path or settings.SYSTEM_PROMPT_PATH
    if not prompt_path.exists():
        return DEFAULT_SYSTEM_PROMPT
    content = prompt_path.read_text(encoding="utf-8").strip()
    return content or DEFAULT_SYSTEM_PROMPT
