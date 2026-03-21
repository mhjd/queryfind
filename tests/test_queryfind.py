from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from queryfind.app import execute_search
from queryfind.config import AppConfig
from queryfind.ollama_client import OllamaClient
from queryfind.benchmark import load_manifest, run_benchmark
from queryfind.models import SearchCandidate
from queryfind.planner import heuristic_intent
from queryfind.search_backend import SearchBackend
from queryfind.logging_utils import RunLogger
from queryfind.synthetic_eval import run_eval


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

    def test_backend_search_handles_command_failures_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logger = RunLogger(root / "test.log", echo=False)
            try:
                backend = SearchBackend(root=root, logger=logger, max_candidates=5)
                intent = heuristic_intent("find any contract file")
                with mock.patch.object(backend, "_run", side_effect=ValueError("Command not allowed: bogus")):
                    candidates = backend.search(intent)
                self.assertEqual(candidates, [])
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

    def test_execute_search_uses_multiple_heuristic_agent_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "contracts").mkdir()
            (root / "contracts" / "client-beta-signed-contract.txt").write_text(
                "Signed contract for client beta.\n",
                encoding="utf-8",
            )
            logger = RunLogger(root / "test.log", echo=False)
            try:
                config = AppConfig(
                    query="find the latest signed contract for client beta",
                    root=root,
                    no_llm=True,
                    max_agent_steps=4,
                )
                execution = execute_search(config, logger)
            finally:
                logger.close()
            self.assertGreaterEqual(len(execution.agent_steps), 2)
            self.assertTrue(execution.outcome.results)
            self.assertEqual(execution.agent_steps[0].action.action, "search_paths")

    def test_execute_search_does_not_fallback_to_heuristic_when_llm_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "contracts").mkdir()
            (root / "contracts" / "client-beta-signed-contract.txt").write_text(
                "Signed contract for client beta.\n",
                encoding="utf-8",
            )
            logger = RunLogger(root / "test.log", echo=False)
            try:
                config = AppConfig(
                    query="find the latest signed contract for client beta",
                    root=root,
                    no_llm=False,
                    max_agent_steps=4,
                )
                execution = execute_search(config, logger, client=None)
            finally:
                logger.close()
            self.assertEqual(len(execution.agent_steps), 1)
            self.assertEqual(execution.agent_steps[0].action.action, "finish")
            self.assertEqual(execution.agent_steps[0].action.source, "backend")
            self.assertEqual(execution.outcome.results, [])

    def test_ranking_without_llm_keeps_backend_order_without_heuristic_fallback(self) -> None:
        from queryfind.planner import rank_results

        config = AppConfig(query="find contract", root=Path("."), no_llm=False)
        logger = RunLogger(Path(tempfile.gettempdir()) / "queryfind-test.log", echo=False)
        try:
            first = SearchCandidate(path=Path("/tmp/a.txt"), score=9.0)
            second = SearchCandidate(path=Path("/tmp/b.txt"), score=4.0)
            outcome = rank_results(
                "find contract",
                candidates=[first, second],
                config=config,
                logger=logger,
                client=None,
            )
        finally:
            logger.close()
        self.assertEqual(outcome.ranking_source, "backend")
        self.assertEqual([item.path for item in outcome.results], [Path("/tmp/a.txt"), Path("/tmp/b.txt")])

    def test_ollama_client_can_attempt_autostart(self) -> None:
        client = OllamaClient("http://127.0.0.1:11434")
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "ollama-serve.log"
            with (
                mock.patch("queryfind.ollama_client.shutil.which", return_value="/opt/homebrew/bin/ollama"),
                mock.patch.object(client, "available", side_effect=[False, False, True]),
                mock.patch("queryfind.ollama_client.time.sleep", return_value=None),
                mock.patch("queryfind.ollama_client.subprocess.Popen") as popen_mock,
            ):
                started = client.ensure_running(timeout=1.0, server_log_path=log_path)
            self.assertTrue(started)
            popen_mock.assert_called_once()

    def test_non_gpt_oss_models_do_not_enable_thinking(self) -> None:
        from queryfind.ollama_client import resolve_think_value

        self.assertFalse(resolve_think_value("qwen3.5:27b", "medium"))
        self.assertEqual(resolve_think_value("gpt-oss:20b", "medium"), "medium")

    def test_synthetic_eval_passes_without_llm(self) -> None:
        results = run_eval(use_llm=False)
        failed = [result.case.name for result in results if not result.success]
        self.assertEqual(failed, [], msg=f"failed synthetic cases: {failed}")

    def test_benchmark_manifest_loads(self) -> None:
        manifest = load_manifest()
        self.assertGreaterEqual(len(manifest.cases), 16)
        self.assertTrue(manifest.corpus_root.exists())

    def test_benchmark_runner_executes_subset_without_llm(self) -> None:
        _, results, summaries, report_path = run_benchmark(
            models=[],
            include_heuristic=True,
            case_names={"latest_redwood_contract", "cinder_harbor_wifi_password", "atlas_owner"},
            repeats=1,
            quiet=True,
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(len(summaries), 1)
        self.assertTrue(report_path.exists())
        self.assertTrue(any(item.success for item in results))


if __name__ == "__main__":
    unittest.main()
