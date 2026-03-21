from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from queryfind.planner import heuristic_intent
from queryfind.search_backend import SearchBackend
from queryfind.logging_utils import RunLogger


class QueryFindTests(unittest.TestCase):
    def test_heuristic_intent_detects_extensions_and_sort(self) -> None:
        intent = heuristic_intent("find the latest beta contract pdf")
        self.assertEqual(intent.sort_hint, "mtime_desc")
        self.assertIn("beta", intent.path_terms)
        self.assertIn("contract", intent.content_terms)
        self.assertIn("pdf", intent.extensions)

    def test_backend_rejects_non_allowlisted_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunLogger(Path(tmpdir) / "test.log")
            try:
                backend = SearchBackend(root=Path(tmpdir), logger=logger, max_candidates=5)
                with self.assertRaises(ValueError):
                    backend._run(["cat", "foo"], allowed_returncodes={0})  # noqa: SLF001
            finally:
                logger.close()

    def test_cli_search_without_llm_finds_matching_file(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "contracts").mkdir()
            (root / "contracts" / "client-beta-signed-contract.txt").write_text(
                "Signed contract for client beta.\n",
                encoding="utf-8",
            )
            (root / "notes.txt").write_text("unrelated notes\n", encoding="utf-8")
            log_dir = root / "logs"
            command = [
                sys.executable,
                "-m",
                "queryfind",
                "find the latest signed contract for client beta",
                "--root",
                str(root),
                "--no-llm",
                "--log-dir",
                str(log_dir),
            ]
            result = subprocess.run(
                command,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("client-beta-signed-contract.txt", result.stdout)


if __name__ == "__main__":
    unittest.main()
