import tempfile
import unittest
from pathlib import Path

from local_agent_memory.mcp_server import handle_request
from local_agent_memory.service import MemoryService


class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.service = MemoryService(Path(self.tmpdir.name) / "memory.db")
        self.service.initialize()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def call_tool(self, name: str, arguments: dict) -> dict:
        response = handle_request(
            self.service,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
        self.assertNotIn("error", response)
        return response["result"]["structuredContent"]

    def test_initialize_and_tools_list(self) -> None:
        initialize = handle_request(
            self.service,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        self.assertEqual("local-agent-memory", initialize["result"]["serverInfo"]["name"])

        tools = handle_request(
            self.service,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )["result"]["tools"]
        self.assertIn("memory_get_pinned", {tool["name"] for tool in tools})
        self.assertIn("memory_update", {tool["name"] for tool in tools})

    def test_mcp_lifecycle_add_pinned_get_unpin_and_repin_through_update(self) -> None:
        created = self.call_tool(
            "memory_add",
            {
                "content": "用户偏好：个人 wiki 笔记默认写中文",
                "scope": "global",
                "kind": "preference",
                "status": "pinned",
            },
        )
        self.assertEqual("pinned", created["status"])
        self.assertEqual("mcp", created["source_kind"])

        pinned = self.call_tool("memory_get_pinned", {"scope": "global"})
        self.assertEqual([created["id"]], [memory["id"] for memory in pinned])

        unpinned = self.call_tool(
            "memory_update", {"id": created["id"], "patch": {"status": "active"}}
        )
        self.assertEqual("active", unpinned["status"])
        self.assertEqual([], self.call_tool("memory_get_pinned", {"scope": "global"}))

        repinned = self.call_tool(
            "memory_update", {"id": created["id"], "patch": {"status": "pinned"}}
        )
        self.assertEqual("pinned", repinned["status"])

    def test_mcp_search_update_and_delete_include_required_fields(self) -> None:
        created = self.call_tool(
            "memory_add",
            {
                "content": "OpenClaw 默认模型是 minimax/MiniMax-M2.5",
                "scope": "project:openclaw",
                "kind": "fact",
                "source_ref": "docs/mvp.md",
            },
        )
        results = self.call_tool(
            "memory_search",
            {"query": "OpenClaw 默认模型", "scope": "project:openclaw"},
        )
        self.assertEqual(created["id"], results[0]["id"])
        for field in (
            "id",
            "content",
            "kind",
            "scope",
            "status",
            "confidence",
            "source_kind",
            "source_ref",
            "created_at",
            "updated_at",
        ):
            self.assertIn(field, results[0])

        deleted = self.call_tool("memory_delete", {"id": created["id"]})
        self.assertEqual("deleted", deleted["status"])


if __name__ == "__main__":
    unittest.main()
