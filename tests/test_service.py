import tempfile
import unittest
from pathlib import Path

from local_agent_memory.service import (
    LifecycleError,
    MemoryService,
    SecretLikeContentError,
    ValidationError,
)


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.service = MemoryService(Path(self.tmpdir.name) / "memory.db")
        self.service.initialize()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_validation_rejects_bad_fields_and_secret_like_content(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.add_memory("hello", scope="workspace", kind="note")
        with self.assertRaises(ValidationError):
            self.service.add_memory("hello", scope="global", kind="unknown")
        with self.assertRaises(ValidationError):
            self.service.add_memory("hello", scope="global", confidence=1.5)
        with self.assertRaises(SecretLikeContentError):
            self.service.add_memory(
                "api_key = abcdefghijklmnopqrstuvwxyz123456",
                scope="global",
            )

    def test_scoped_pinned_retrieval_returns_exact_scope_plus_global(self) -> None:
        global_memory = self.service.add_memory("全局偏好", scope="global", pin=True)
        project_memory = self.service.add_memory("项目偏好", scope="project:openclaw", pin=True)
        self.service.add_memory("其他项目偏好", scope="project:other", pin=True)

        pinned = self.service.get_pinned(scope="project:openclaw")
        self.assertEqual([project_memory.id, global_memory.id], [memory.id for memory in pinned])

    def test_pin_unpin_service_rejects_inactive_lifecycle_statuses(self) -> None:
        memory = self.service.add_memory("生命周期测试", scope="global")
        pinned = self.service.pin_memory(memory.id)
        self.assertEqual("pinned", pinned.status)
        unpinned = self.service.update_memory(memory.id, {"status": "active"})
        self.assertEqual("active", unpinned.status)

        expired = self.service.update_memory(memory.id, {"status": "expired"})
        with self.assertRaises(LifecycleError):
            self.service.pin_memory(expired.id)
        with self.assertRaises(LifecycleError):
            self.service.update_memory(expired.id, {"status": "pinned"})

    def test_scope_aware_search_returns_provenance_and_excludes_inactive_by_default(self) -> None:
        global_memory = self.service.add_memory(
            "OpenClaw 默认模型是 minimax/MiniMax-M2.5",
            scope="global",
            kind="fact",
            source_kind="manual",
            source_ref="docs/mvp.md",
        )
        project_memory = self.service.add_memory(
            "OpenClaw gateway port is 18789",
            scope="project:openclaw",
            kind="fact",
        )
        other_memory = self.service.add_memory("OpenClaw unrelated", scope="project:other")
        self.service.delete_memory(other_memory.id)

        results = self.service.search("OpenClaw", scope="project:openclaw", limit=10)
        self.assertEqual({global_memory.id, project_memory.id}, {memory.id for memory in results})
        self.assertTrue(all(memory.source_kind for memory in results))
        self.assertTrue(all(memory.created_at for memory in results))

    def test_supersede_flow_marks_old_memory_and_audits_write(self) -> None:
        old = self.service.add_memory("OpenClaw 默认模型是旧模型", scope="project:openclaw")
        new = self.service.supersede_memory(old.id, "OpenClaw 默认模型是 minimax/MiniMax-M2.5")

        self.assertEqual("active", new.status)
        self.assertEqual("superseded", self.service.get_memory(old.id).status)
        events = [event.event_type for event in self.service.repo.list_events(old.id)]
        self.assertIn("superseded", events)


if __name__ == "__main__":
    unittest.main()
