from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import shlex
import sys
from typing import TextIO


@dataclass(slots=True)
class RunLogger:
    log_path: Path
    echo: bool = True
    _handle: TextIO = field(init=False, repr=False)
    _stream_open: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.log_path.open("a", encoding="utf-8")

    def close(self) -> None:
        if self._stream_open:
            self._write_stream("", end="\n")
            self._stream_open = False
        self._handle.close()

    def info(self, message: str) -> None:
        self._log("INFO", message)

    def warn(self, message: str) -> None:
        self._log("WARN", message)

    def error(self, message: str) -> None:
        self._log("ERROR", message)

    def command(self, argv: list[str]) -> None:
        self._log("INFO", f"exec {shlex.join(argv)}")

    def start_stream(self, label: str) -> None:
        self._log("INFO", label)
        self._stream_open = True

    def write_stream(self, text: str) -> None:
        self._write_stream(text, end="")

    def end_stream(self) -> None:
        if self._stream_open:
            self._write_stream("", end="\n")
            self._stream_open = False

    def _log(self, level: str, message: str) -> None:
        if self._stream_open:
            self._write_stream("", end="\n")
            self._stream_open = False
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {level:<5} {message}"
        if self.echo:
            print(line)
        self._handle.write(line + "\n")
        self._handle.flush()

    def _write_stream(self, text: str, end: str) -> None:
        if self.echo:
            sys.stdout.write(text + end)
            sys.stdout.flush()
        self._handle.write(text + end)
        self._handle.flush()
