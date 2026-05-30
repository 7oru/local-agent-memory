import tempfile
import unittest
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient  # noqa: E402

from local_agent_memory.api import create_app  # noqa: E402


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "memory.db"
        self.client = TestClient(create_app(self.db_path))

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["ok"])

    def test_web_ui_contains_core_surfaces(self) -> None:
        response = self.client.get("/")
        self.assertEqual(200, response.status_code)
        html = response.text
        for text in ("Pinned", "Search", "Settings", "Add Memory", "Supersede", "mcpServers"):
            self.assertIn(text, html)
        self.assertIn("function snippet", html)
        self.assertIn("aria-busy", html)

    def test_http_lifecycle_pin_get_pinned_unpin_and_repin(self) -> None:
        created_response = self.client.post(
            "/memories",
            json={
                "content": "用户偏好：个人 wiki 笔记默认写中文",
                "scope": "global",
                "kind": "preference",
                "pin": True,
            },
        )
        self.assertEqual(201, created_response.status_code)
        created = created_response.json()
        self.assertEqual("pinned", created["status"])
        self.assertEqual("api", created["source_kind"])

        pinned = self.client.get("/pinned", params={"scope": "global"}).json()
        self.assertEqual([created["id"]], [memory["id"] for memory in pinned])

        unpinned_response = self.client.patch(
            f"/memories/{created['id']}", json={"status": "active"}
        )
        self.assertEqual(200, unpinned_response.status_code)
        self.assertEqual("active", unpinned_response.json()["status"])
        self.assertEqual([], self.client.get("/pinned", params={"scope": "global"}).json())

        repinned_response = self.client.patch(
            f"/memories/{created['id']}", json={"status": "pinned"}
        )
        self.assertEqual(200, repinned_response.status_code)
        self.assertEqual("pinned", repinned_response.json()["status"])

    def test_http_search_delete_and_export(self) -> None:
        created = self.client.post(
            "/memories",
            json={
                "content": "OpenClaw 默认模型是 minimax/MiniMax-M2.5",
                "scope": "project:openclaw",
                "kind": "fact",
                "source_ref": "docs/mvp.md",
            },
        ).json()

        search_response = self.client.post(
            "/search",
            json={"query": "OpenClaw 默认模型", "scope": "project:openclaw"},
        )
        self.assertEqual(200, search_response.status_code)
        self.assertEqual(created["id"], search_response.json()[0]["id"])
        self.assertEqual("docs/mvp.md", search_response.json()[0]["source_ref"])

        deleted_response = self.client.delete(f"/memories/{created['id']}")
        self.assertEqual(200, deleted_response.status_code)
        self.assertEqual("deleted", deleted_response.json()["status"])

        export = self.client.get("/export").json()
        self.assertEqual("deleted", export["memories"][0]["status"])
        self.assertIn("deleted", [event["event_type"] for event in export["events"]])

    def test_http_supersede_endpoint(self) -> None:
        created = self.client.post(
            "/memories",
            json={"content": "OpenClaw 默认模型是旧模型", "scope": "project:openclaw"},
        ).json()

        new_response = self.client.post(
            f"/memories/{created['id']}/supersede",
            json={"content": "OpenClaw 默认模型是 minimax/MiniMax-M2.5"},
        )
        self.assertEqual(201, new_response.status_code)
        self.assertEqual("active", new_response.json()["status"])
        old = self.client.get(f"/memories/{created['id']}").json()
        self.assertEqual("superseded", old["status"])


if __name__ == "__main__":
    unittest.main()
