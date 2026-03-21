from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "qwen3.5:27b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
ALLOWED_COMMANDS = ("fd", "rg", "ls", "tree", "stat", "mdls")
REQUIRED_COMMANDS = ("fd", "rg")


@dataclass(slots=True)
class AppConfig:
    query: str | None
    root: Path
    model: str = DEFAULT_MODEL
    ollama_url: str = DEFAULT_OLLAMA_URL
    think_level: str = "medium"
    ollama_request_timeout: float = 30.0
    max_agent_steps: int = 4
    max_candidates: int = 20
    max_results: int = 5
    no_llm: bool = False
    show_thinking: bool = True
    ollama_autostart: bool = True
    ollama_start_timeout: float = 12.0
    log_dir: Path | None = None

    @property
    def resolved_root(self) -> Path:
        return self.root.expanduser().resolve()

    @property
    def resolved_log_dir(self) -> Path:
        base = self.log_dir or (Path.cwd() / ".queryfind" / "logs")
        return base.expanduser().resolve()
