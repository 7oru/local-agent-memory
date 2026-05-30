import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_agent_memory.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "memory.db")
        self.env = patch.dict(os.environ, {"LAM_DB_PATH": self.db_path})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmpdir.cleanup()

    def run_cli(self, args: list[str]) -> str:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(args)
        self.assertEqual(0, code, stdout.getvalue())
        return stdout.getvalue()

    def test_cli_lifecycle_add_pin_list_unpin_and_pin_again(self) -> None:
        self.run_cli(["init"])
        created = json.loads(
            self.run_cli(
                [
                    "add",
                    "用户偏好：个人 wiki 笔记默认写中文",
                    "--scope",
                    "global",
                    "--kind",
                    "preference",
                    "--pin",
                    "--json",
                ]
            )
        )

        pinned = json.loads(
            self.run_cli(["list", "--scope", "global", "--status", "pinned", "--json"])
        )
        self.assertEqual([created["id"]], [memory["id"] for memory in pinned])
        self.assertEqual("cli", pinned[0]["source_kind"])
        self.assertTrue(pinned[0]["created_at"])

        unpinned = json.loads(self.run_cli(["unpin", created["id"], "--json"]))
        self.assertEqual("active", unpinned["status"])
        pinned_after_unpin = json.loads(
            self.run_cli(["list", "--scope", "global", "--status", "pinned", "--json"])
        )
        self.assertEqual([], pinned_after_unpin)

        pinned_again = json.loads(self.run_cli(["pin", created["id"], "--json"]))
        self.assertEqual("pinned", pinned_again["status"])

    def test_cli_search_and_export_include_provenance(self) -> None:
        created = json.loads(
            self.run_cli(
                [
                    "add",
                    "OpenClaw 默认模型是 minimax/MiniMax-M2.5",
                    "--scope",
                    "project:openclaw",
                    "--kind",
                    "fact",
                    "--source-ref",
                    "docs/mvp.md",
                    "--json",
                ]
            )
        )

        results = json.loads(
            self.run_cli(["search", "OpenClaw 默认模型", "--scope", "project:openclaw", "--json"])
        )
        self.assertEqual(created["id"], results[0]["id"])
        self.assertEqual("docs/mvp.md", results[0]["source_ref"])

        exported = json.loads(self.run_cli(["export"]))
        self.assertEqual(created["id"], exported["memories"][0]["id"])
        self.assertTrue(exported["events"])


if __name__ == "__main__":
    unittest.main()
