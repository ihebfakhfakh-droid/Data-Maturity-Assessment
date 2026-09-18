from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3.5:9b"
    USE_OLLAMA: bool = True
    AUTO_COMPLETE_BEST_PATH: bool = False
    OPENAI_TIMEOUT_SECONDS: int = 9000
    OLLAMA_TIMEOUT_SECONDS: int = 9000

    # Optional legacy aliases still accepted from environment.
    LLM_API_URL: str | None = None
    LLM_MODEL: str | None = None
    LLM_TIMEOUT_SECONDS: int | None = None
    LLM_PROVIDER: str = "ollama"

    FRAMEWORK_PATH: Path = BASE_DIR / "app" / "data" / "ndi_framework.json"
    SYSTEM_PROMPT_PATH: Path = BASE_DIR / "prompts" / "system_prompt.txt"
    DEBUG_PAYLOAD_PATH: Path = BASE_DIR / "debug" / "latest_ollama_payload.json"
    DEBUG_CANDIDATE_ACTIONS_PATH: Path = BASE_DIR / "debug" / "latest_candidate_actions.json"
    DEBUG_ALLOWED_ACTION_IDS_PATH: Path = BASE_DIR / "debug" / "latest_allowed_action_ids.json"

    @property
    def ollama_chat_url(self) -> str:
        if self.LLM_API_URL:
            return self.LLM_API_URL
        return f"{self.OLLAMA_BASE_URL.rstrip('/')}/api/chat"

    @property
    def effective_ollama_model(self) -> str:
        return self.OLLAMA_MODEL or self.LLM_MODEL or "qwen3.5:9b"

    @property
    def effective_ollama_timeout(self) -> int:
        if self.OLLAMA_TIMEOUT_SECONDS:
            return self.OLLAMA_TIMEOUT_SECONDS
        if self.OPENAI_TIMEOUT_SECONDS:
            return self.OPENAI_TIMEOUT_SECONDS
        if self.LLM_TIMEOUT_SECONDS:
            return self.LLM_TIMEOUT_SECONDS
        return 9000


settings = Settings()
