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

    def test_root_redirects_to_pinned_ui_route(self) -> None:
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(307, response.status_code)
        self.assertEqual("/app/pinned", response.headers["location"])

    def test_web_ui_contains_core_surfaces(self) -> None:
        response = self.client.get("/app/search")
        self.assertEqual(200, response.status_code)
        html = response.text
        for text in (
            "Pinned",
            "Search",
            "Settings",
            "Add Memory",
            "Supersede",
            "Audit Events",
            "Normalized Schema",
            "Metadata JSON",
            "Tags",
            "mcpServers",
        ):
            self.assertIn(text, html)
        self.assertIn("function snippet", html)
        self.assertIn("aria-busy", html)
        self.assertIn("/memories?", html)
        self.assertIn("/events", html)
        self.assertIn("detail-content-preview", html)
        self.assertIn("Loading memories...", html)
        self.assertIn("/app/pinned", html)
        self.assertIn("/app/search", html)
        self.assertIn("/app/settings", html)
        self.assertIn("history.pushState", html)
        self.assertIn("popstate", html)

    def test_ui_routes_do_not_replace_api_routes(self) -> None:
        self.assertEqual(200, self.client.get("/app/pinned").status_code)
        self.assertEqual(200, self.client.get("/app/settings").status_code)
        pinned_response = self.client.get("/pinned")
        self.assertEqual(200, pinned_response.status_code)
        self.assertEqual([], pinned_response.json())
        missing_response = self.client.get("/app/unknown")
        self.assertEqual(404, missing_response.status_code)

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
                "content": "默认模型是 minimax/MiniMax-M2.5",
                "scope": "project:openclaw",
                "title": "OpenClaw default model",
                "subject": "OpenClaw",
                "entities": ["OpenClaw", "MiniMax-M2.5"],
                "relations": [
                    {
                        "subject": "OpenClaw",
                        "predicate": "uses_model",
                        "object": "MiniMax-M2.5",
                    }
                ],
                "salience": 0.9,
                "privacy": "personal",
                "retention": "long_term",
                "user_id": "rick",
                "kind": "fact",
                "source_ref": "docs/mvp.md",
            },
        ).json()
        self.assertEqual("lam.memory.v1", created["schema_version"])
        self.assertEqual("OpenClaw", created["subject"])
        self.assertEqual(["OpenClaw", "MiniMax-M2.5"], created["entities"])
        self.assertEqual(0.9, created["salience"])
        self.assertEqual("long_term", created["retention"])
        self.assertEqual("rick", created["user_id"])

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

    def test_http_patch_can_clear_nullable_detail_fields(self) -> None:
        created = self.client.post(
            "/memories",
            json={
                "content": "Detail edits can clear stale optional metadata",
                "scope": "project:local-agent-memory",
                "title": "stale title",
                "summary": "stale summary",
                "subject": "stale subject",
                "source_ref": "docs/old.md",
                "user_id": "old-user",
                "agent_id": "old-agent",
                "app_id": "old-app",
                "run_id": "old-run",
            },
        ).json()

        response = self.client.patch(
            f"/memories/{created['id']}",
            json={
                "title": None,
                "summary": None,
                "subject": None,
                "source_ref": None,
                "user_id": None,
                "agent_id": None,
                "app_id": None,
                "run_id": None,
            },
        )

        self.assertEqual(200, response.status_code)
        updated = response.json()
        for field in (
            "title",
            "summary",
            "subject",
            "source_ref",
            "user_id",
            "agent_id",
            "app_id",
            "run_id",
        ):
            self.assertIsNone(updated[field])

        export = self.client.get("/export").json()
        exported = export["memories"][0]
        self.assertEqual(created["id"], exported["id"])
        self.assertIsNone(exported["title"])
        self.assertIsNone(exported["source_ref"])
        self.assertIsNone(exported["user_id"])

    def test_http_search_can_return_limited_content_for_fast_tables(self) -> None:
        long_content = "Kimi reviewer verdict: " + ("practical MVP ready " * 80)
        created = self.client.post(
            "/memories",
            json={
                "content": long_content,
                "scope": "project:local-agent-memory",
                "kind": "task_state",
            },
        ).json()

        search_response = self.client.post(
            "/search",
            json={
                "query": "Kimi practical MVP ready",
                "scope": "project:local-agent-memory",
                "content_limit": 80,
            },
        )
        self.assertEqual(200, search_response.status_code)
        result = search_response.json()[0]
        self.assertEqual(created["id"], result["id"])
        self.assertLessEqual(len(result["content"]), 80)
        self.assertTrue(result["content_truncated"])
        self.assertEqual(len(long_content.strip()), result["content_length"])

        full = self.client.get(f"/memories/{created['id']}").json()
        self.assertEqual(long_content.strip(), full["content"])

    def test_memory_events_endpoint_returns_audit_history(self) -> None:
        created = self.client.post(
            "/memories",
            json={
                "content": "Detail UI should expose memory audit history",
                "scope": "project:local-agent-memory",
                "kind": "task_state",
            },
        ).json()

        self.client.patch(f"/memories/{created['id']}", json={"status": "pinned"})

        response = self.client.get(f"/memories/{created['id']}/events")
        self.assertEqual(200, response.status_code)
        events = response.json()
        self.assertEqual(["created", "pinned"], [event["event_type"] for event in events])
        self.assertEqual(created["id"], events[0]["memory_id"])

        missing_response = self.client.get("/memories/missing/events")
        self.assertEqual(404, missing_response.status_code)

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
