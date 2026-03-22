from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from queryfind.app import execute_search, prewarm_search_client
from queryfind.config import AppConfig
from queryfind.ollama_client import (
    OllamaChunk,
    OllamaClient,
    OllamaConfigurationError,
    OllamaUnavailableError,
)
from queryfind.benchmark import (
    EXTENDED_BENCHMARK_MANIFEST_PATH,
    HANDMADE_BENCHMARK_MANIFEST_PATH,
    MEGA_BENCHMARK_MANIFEST_PATH,
    load_manifest,
    run_benchmark,
)
from queryfind.models import SearchCandidate, SearchIntent
from queryfind.planner import heuristic_intent, next_agent_action
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

    def test_backend_rejects_invalid_flags_for_allowlisted_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logger = RunLogger(root / "test.log", echo=False)
            try:
                backend = SearchBackend(root=root, logger=logger, max_candidates=5)
                with self.assertRaises(ValueError):
                    backend._run(["rg", "--files", str(root)], allowed_returncodes={0})  # noqa: SLF001
            finally:
                logger.close()

    def test_backend_skips_suspicious_leading_dash_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "note.txt").write_text("hello world\n", encoding="utf-8")
            logger = RunLogger(root / "test.log", echo=False)
            try:
                backend = SearchBackend(root=root, logger=logger, max_candidates=5)
                candidates = backend.search(
                    SearchIntent(query_summary="find hello", content_terms=["--files"], path_terms=["--files"])
                )
            finally:
                logger.close()
            self.assertEqual(candidates, [])
            log_text = (root / "test.log").read_text(encoding="utf-8")
            self.assertIn("skipped suspicious term", log_text)

    def test_backend_search_does_not_escape_root_via_symlink(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.TemporaryDirectory() as outside_tmpdir,
            tempfile.TemporaryDirectory() as log_tmpdir,
        ):
            root = Path(tmpdir)
            outside_root = Path(outside_tmpdir)
            outside_file = outside_root / "outside-secret.txt"
            outside_file.write_text("secret\n", encoding="utf-8")
            (root / "outside-link.txt").symlink_to(outside_file)
            logger = RunLogger(Path(log_tmpdir) / "test.log", echo=False)
            try:
                backend = SearchBackend(root=root, logger=logger, max_candidates=5)
                candidates = backend.search(
                    SearchIntent(
                        query_summary="find outside link",
                        path_terms=["outside"],
                        filename_hints=["outside"],
                    )
                )
            finally:
                logger.close()
            self.assertEqual(candidates, [])

    def test_backend_uses_trusted_binaries_instead_of_path_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as log_tmpdir:
            root = Path(tmpdir)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            marker = root / "fake-rg-hit.txt"
            fake_rg = fake_bin / "rg"
            fake_rg.write_text(f"#!/bin/sh\necho fake >> {marker}\nexit 0\n", encoding="utf-8")
            fake_rg.chmod(0o755)
            (root / "note.txt").write_text("hello world\n", encoding="utf-8")
            logger = RunLogger(Path(log_tmpdir) / "test.log", echo=False)
            try:
                with mock.patch.dict("os.environ", {"PATH": f"{fake_bin}:{root}"}, clear=False):
                    backend = SearchBackend(root=root, logger=logger, max_candidates=5)
                    candidates = backend.search(
                        SearchIntent(query_summary="find hello", content_terms=["hello"])
                    )
            finally:
                logger.close()
            self.assertFalse(marker.exists())
            self.assertEqual([candidate.path.name for candidate in candidates], ["note.txt"])

    def test_backend_command_env_does_not_inherit_ripgrep_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logger = RunLogger(root / "test.log", echo=False)
            try:
                with mock.patch.dict("os.environ", {"RIPGREP_CONFIG_PATH": "/tmp/evil-rg-config"}, clear=False):
                    backend = SearchBackend(root=root, logger=logger, max_candidates=5)
                    env = backend._command_env()  # noqa: SLF001
            finally:
                logger.close()
            self.assertNotIn("RIPGREP_CONFIG_PATH", env)

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

    def test_prewarm_search_client_calls_client_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunLogger(Path(tmpdir) / "test.log", echo=False)
            try:
                client = mock.Mock()
                config = AppConfig(
                    query="find contract",
                    root=Path(tmpdir),
                    no_llm=False,
                    ollama_prewarm=True,
                    ollama_keep_alive="30m",
                )
                prewarm_search_client(config, logger, client=client)
            finally:
                logger.close()
            client.prewarm.assert_called_once_with(model=config.model, keep_alive="30m")

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

    def test_agent_step_uses_streaming_in_hidden_thinking_mode(self) -> None:
        class FakeStreamingClient:
            def chat_stream(
                self,
                *,
                model: str,
                messages: list[dict[str, str]],
                think: str | bool,
                keep_alive: str | int | None = None,
            ):
                del model, messages, think, keep_alive
                yield OllamaChunk(content='{"action":"finish","terms":[],"extensions":[],"reasoning":"done","final_summary":"done"}')

            def chat_json(self, *, model: str, messages: list[dict[str, str]], think: str | bool):
                del model, messages, think
                raise AssertionError("chat_json should not be called for agent steps in hidden-thinking mode")

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunLogger(Path(tmpdir) / "test.log", echo=False)
            try:
                action = next_agent_action(
                    "find contract",
                    root_overview="contracts notes",
                    candidates=[],
                    steps=[],
                    config=AppConfig(query="find contract", root=Path(tmpdir), no_llm=False, show_thinking=False),
                    logger=logger,
                    client=FakeStreamingClient(),  # type: ignore[arg-type]
                )
            finally:
                logger.close()
            self.assertEqual(action.action, "finish")
            self.assertEqual(action.source, "ollama")
            log_text = (Path(tmpdir) / "test.log").read_text(encoding="utf-8")
            self.assertIn("streaming diagnostics mode", log_text)
            self.assertIn("stream diagnostics: status=completed", log_text)

    def test_agent_step_can_use_partial_streamed_json_before_timeout(self) -> None:
        class FakePartialStreamingClient:
            def chat_stream(
                self,
                *,
                model: str,
                messages: list[dict[str, str]],
                think: str | bool,
                keep_alive: str | int | None = None,
            ):
                del model, messages, think, keep_alive
                yield OllamaChunk(content='{"action":"finish","terms":[],"extensions":[],"reasoning":"done","final_summary":"done"}')
                raise OllamaUnavailableError("timed out")

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunLogger(Path(tmpdir) / "test.log", echo=False)
            try:
                action = next_agent_action(
                    "find contract",
                    root_overview="contracts notes",
                    candidates=[],
                    steps=[],
                    config=AppConfig(query="find contract", root=Path(tmpdir), no_llm=False, show_thinking=False),
                    logger=logger,
                    client=FakePartialStreamingClient(),  # type: ignore[arg-type]
                )
            finally:
                logger.close()
            self.assertEqual(action.action, "finish")
            self.assertEqual(action.source, "ollama")
            log_text = (Path(tmpdir) / "test.log").read_text(encoding="utf-8")
            self.assertIn("stream diagnostics: status=interrupted", log_text)
            self.assertIn("attempting to use partial streamed output", log_text)

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

    def test_ollama_client_rejects_remote_url_by_default(self) -> None:
        with self.assertRaises(OllamaConfigurationError):
            OllamaClient("https://example.com:11434")

    def test_ollama_client_allows_remote_url_with_explicit_opt_in(self) -> None:
        client = OllamaClient("https://example.com:11434", allow_remote=True)
        self.assertFalse(client.endpoint_is_local)

    def test_remote_ollama_endpoint_does_not_autostart_local_server(self) -> None:
        from queryfind.app import resolve_search_client

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunLogger(Path(tmpdir) / "test.log", echo=False)
            try:
                config = AppConfig(
                    query="find contract",
                    root=Path(tmpdir),
                    no_llm=False,
                    ollama_url="https://example.com:11434",
                    allow_remote_ollama=True,
                    ollama_autostart=True,
                )
                with (
                    mock.patch("queryfind.app.OllamaClient.available", return_value=False),
                    mock.patch("queryfind.app.OllamaClient.ensure_running") as ensure_running_mock,
                ):
                    client = resolve_search_client(config, logger, timestamp="20260322-remote")
            finally:
                logger.close()
            self.assertIsNone(client)
            ensure_running_mock.assert_not_called()
            log_text = (Path(tmpdir) / "test.log").read_text(encoding="utf-8")
            self.assertIn("automatic startup is disabled for non-local URLs", log_text)

    def test_structured_outputs_do_not_enable_thinking(self) -> None:
        from queryfind.ollama_client import resolve_think_value

        self.assertFalse(resolve_think_value("qwen3.5:27b", "medium"))
        self.assertFalse(resolve_think_value("gpt-oss:20b", "medium"))

    def test_agent_step_can_use_streamed_thinking_when_content_is_empty(self) -> None:
        class FakeThinkingOnlyClient:
            def chat_stream(
                self,
                *,
                model: str,
                messages: list[dict[str, str]],
                think: str | bool,
                keep_alive: str | int | None = None,
            ):
                del model, messages, think, keep_alive
                yield OllamaChunk(thinking='{"action":"finish","terms":[],"extensions":[],"reasoning":"done","final_summary":"done"}')

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunLogger(Path(tmpdir) / "test.log", echo=False)
            try:
                action = next_agent_action(
                    "find contract",
                    root_overview="contracts notes",
                    candidates=[],
                    steps=[],
                    config=AppConfig(query="find contract", root=Path(tmpdir), no_llm=False, show_thinking=False),
                    logger=logger,
                    client=FakeThinkingOnlyClient(),  # type: ignore[arg-type]
                )
            finally:
                logger.close()
            self.assertEqual(action.action, "finish")
            self.assertEqual(action.source, "ollama")
            log_text = (Path(tmpdir) / "test.log").read_text(encoding="utf-8")
            self.assertIn("using thinking text as parse fallback", log_text)

    def test_synthetic_eval_passes_without_llm(self) -> None:
        results = run_eval(use_llm=False)
        failed = [result.case.name for result in results if not result.success]
        self.assertEqual(failed, [], msg=f"failed synthetic cases: {failed}")

    def test_benchmark_manifest_loads(self) -> None:
        manifest = load_manifest()
        self.assertGreaterEqual(len(manifest.cases), 16)
        self.assertTrue(manifest.corpus_root.exists())

    def test_extended_benchmark_manifest_loads(self) -> None:
        manifest = load_manifest(EXTENDED_BENCHMARK_MANIFEST_PATH)
        self.assertEqual(len(manifest.cases), 40)
        self.assertTrue(manifest.corpus_root.exists())

    def test_mega_benchmark_manifest_loads(self) -> None:
        manifest = load_manifest(MEGA_BENCHMARK_MANIFEST_PATH)
        self.assertEqual(len(manifest.cases), 100)
        self.assertTrue(manifest.corpus_root.exists())

    def test_handmade_benchmark_manifest_loads(self) -> None:
        manifest = load_manifest(HANDMADE_BENCHMARK_MANIFEST_PATH)
        self.assertEqual(len(manifest.cases), 125)
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

    def test_extended_benchmark_runner_executes_subset_without_llm(self) -> None:
        _, results, summaries, report_path = run_benchmark(
            manifest_path=EXTENDED_BENCHMARK_MANIFEST_PATH,
            models=[],
            include_heuristic=True,
            case_names={"shipment_8842_delay_reason", "no_mercury_invoice"},
            repeats=1,
            quiet=True,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(len(summaries), 1)
        self.assertTrue(report_path.exists())

    def test_mega_benchmark_runner_executes_subset_without_llm(self) -> None:
        _, results, summaries, report_path = run_benchmark(
            manifest_path=MEGA_BENCHMARK_MANIFEST_PATH,
            models=[],
            include_heuristic=True,
            case_names={"latest_redwood_contract", "cinder-harbor_wifi_password", "atlas_owner"},
            repeats=1,
            quiet=True,
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(len(summaries), 1)
        self.assertTrue(report_path.exists())

    def test_handmade_benchmark_runner_executes_subset_without_llm(self) -> None:
        _, results, summaries, report_path = run_benchmark(
            manifest_path=HANDMADE_BENCHMARK_MANIFEST_PATH,
            models=[],
            include_heuristic=True,
            case_names={"customer_alias_note", "archive_room_code", "guest_network_policy"},
            repeats=1,
            quiet=True,
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(len(summaries), 1)
        self.assertTrue(report_path.exists())


if __name__ == "__main__":
    unittest.main()
