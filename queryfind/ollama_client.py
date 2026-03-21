from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import error, request


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama server is unavailable."""


@dataclass(slots=True)
class OllamaChunk:
    thinking: str = ""
    content: str = ""
    done: bool = False


class OllamaClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

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

    def chat_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        think: str | bool,
    ):
        body = {
            "model": model,
            "messages": messages,
            "think": think,
            "stream": True,
        }
        data = json.dumps(body).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
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

    def _request_json(self, method: str, path: str) -> dict:
        raw = self._request(method, path, None)
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
            with request.urlopen(req, timeout=60) as response:
                return response.read().decode("utf-8")
        except (error.URLError, ConnectionError, TimeoutError) as exc:
            raise OllamaUnavailableError(str(exc)) from exc


def resolve_think_value(model: str, think_level: str) -> str | bool:
    if model.startswith("gpt-oss"):
        return think_level
    return True
