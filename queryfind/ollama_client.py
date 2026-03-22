from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import urlparse
from urllib import error, request


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama server is unavailable."""


class OllamaConfigurationError(ValueError):
    """Raised when the Ollama endpoint configuration is unsafe."""


@dataclass(slots=True)
class OllamaChunk:
    thinking: str = ""
    content: str = ""
    done: bool = False


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        *,
        request_timeout: float = 30.0,
        allow_remote: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.allow_remote = allow_remote
        self._endpoint_host = self._validated_endpoint_host()

    @property
    def endpoint_is_local(self) -> bool:
        return self._endpoint_host in {"127.0.0.1", "localhost", "::1"}

    def available(self) -> bool:
        try:
            self.tags()
        except OllamaUnavailableError:
            return False
        return True

    def tags(self) -> list[str]:
        payload = self._request_json("GET", "/api/tags")
        models = payload.get("models", [])
        return [item.get("name", "") for item in models]

    def ensure_running(self, *, timeout: float, server_log_path: Path | None = None) -> bool:
        if self.available():
            return True
        if not self.endpoint_is_local:
            return False
        if shutil.which("ollama") is None:
            return False

        stdout_handle = None
        stdout_target: int | subprocess.PIPE | None = subprocess.DEVNULL
        stderr_target: int | subprocess.PIPE | None = subprocess.DEVNULL
        if server_log_path is not None:
            server_log_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_handle = server_log_path.open("a", encoding="utf-8")
            stdout_target = stdout_handle
            stderr_target = subprocess.STDOUT

        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdin=subprocess.DEVNULL,
                stdout=stdout_target,
                stderr=stderr_target,
                start_new_session=True,
            )
        except OSError:
            if stdout_handle is not None:
                stdout_handle.close()
            return False
        finally:
            if stdout_handle is not None:
                stdout_handle.close()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.available():
                return True
            time.sleep(0.25)
        return False

    def chat_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        think: str | bool,
        keep_alive: str | int | None = None,
    ):
        body = {
            "model": model,
            "messages": messages,
            "think": think,
            "stream": True,
        }
        if keep_alive is not None:
            body["keep_alive"] = keep_alive
        data = json.dumps(body).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.request_timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if "error" in event:
                        raise OllamaUnavailableError(str(event["error"]))
                    message = event.get("message", {})
                    yield OllamaChunk(
                        thinking=message.get("thinking", ""),
                        content=message.get("content", ""),
                        done=bool(event.get("done")),
                    )
        except (error.URLError, ConnectionError, TimeoutError) as exc:
            raise OllamaUnavailableError(str(exc)) from exc

    def _validated_endpoint_host(self) -> str:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise OllamaConfigurationError("Ollama URL must use http or https")
        if not parsed.hostname:
            raise OllamaConfigurationError("Ollama URL must include a host")
        if not self.allow_remote and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise OllamaConfigurationError(
                "Remote Ollama endpoints are disabled by default; use --allow-remote-ollama to opt in"
            )
        return parsed.hostname

    def chat_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        think: str | bool,
        keep_alive: str | int | None = None,
    ) -> str:
        body = {
            "model": model,
            "messages": messages,
            "think": think,
            "stream": False,
            "format": "json",
        }
        if keep_alive is not None:
            body["keep_alive"] = keep_alive
        payload = self._request_json("POST", "/api/chat", body)
        if "error" in payload:
            raise OllamaUnavailableError(str(payload["error"]))
        message = payload.get("message", {})
        return str(message.get("content", "")).strip()

    def prewarm(self, *, model: str, keep_alive: str | int | None = None) -> None:
        body: dict[str, object] = {
            "model": model,
            "prompt": "",
            "stream": False,
        }
        if keep_alive is not None:
            body["keep_alive"] = keep_alive
        payload = self._request_json("POST", "/api/generate", body)
        if "error" in payload:
            raise OllamaUnavailableError(str(payload["error"]))

    def _request_json(self, method: str, path: str, body: dict | None = None) -> dict:
        raw = self._request(method, path, body)
        return json.loads(raw or "{}")

    def _request(self, method: str, path: str, body: dict | None) -> str:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.request_timeout) as response:
                return response.read().decode("utf-8")
        except (error.URLError, ConnectionError, TimeoutError) as exc:
            raise OllamaUnavailableError(str(exc)) from exc


def resolve_think_value(model: str, think_level: str) -> str | bool:
    del model, think_level
    return False
