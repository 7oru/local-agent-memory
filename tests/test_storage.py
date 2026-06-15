import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from local_agent_memory.storage import InvalidTransitionError, MemoryRepository, connect


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "memory.db"
        self.repo = MemoryRepository(self.db_path)
        self.repo.initialize()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_create_search_update_delete_and_export(self) -> None:
        memory = self.repo.create_memory(
            "OpenClaw 默认模型是 minimax/MiniMax-M2.5",
            "project:openclaw",
            title="OpenClaw default model",
            subject="OpenClaw",
            entities=["OpenClaw", "MiniMax-M2.5"],
            relations=[
                {"subject": "OpenClaw", "predicate": "uses_model", "object": "MiniMax-M2.5"}
            ],
            kind="fact",
            source_kind="manual",
            source_ref="test",
            user_id="rick",
            agent_id="codex",
            app_id="local-agent-memory",
            run_id="test-run",
        )

        search_results = self.repo.search("OpenClaw 默认模型", scope="project:openclaw")
        self.assertEqual([memory.id], [item.id for item in search_results])
        self.assertEqual("lam.memory.v1", search_results[0].schema_version)
        self.assertEqual("OpenClaw", search_results[0].subject)
        self.assertEqual(["OpenClaw", "MiniMax-M2.5"], search_results[0].entities)
        self.assertEqual("rick", search_results[0].user_id)
        self.assertEqual("manual", search_results[0].source_kind)
        self.assertIsNotNone(search_results[0].created_at)
        self.assertEqual(
            [memory.id], [item.id for item in self.repo.list_memories(scope="project:openclaw")]
        )

        updated = self.repo.update_memory(
            memory.id, {"content": "OpenClaw 默认模型是 MiniMax-M2.5"}
        )
        self.assertEqual("OpenClaw 默认模型是 MiniMax-M2.5", updated.content)

        deleted = self.repo.soft_delete(memory.id)
        self.assertEqual("deleted", deleted.status)
        self.assertEqual([], self.repo.search("OpenClaw", scope="project:openclaw"))

        exported = self.repo.export_json()
        self.assertEqual("lam.memory.v1", exported["schema_version"])
        self.assertEqual(1, len(exported["memories"]))
        self.assertEqual("deleted", exported["memories"][0]["status"])
        self.assertIn("deleted", [event["event_type"] for event in exported["events"]])

    def test_export_json_includes_more_than_default_list_limit(self) -> None:
        created_ids = {
            self.repo.create_memory(f"backup memory {index}", "global").id
            for index in range(101)
        }

        self.assertEqual(100, len(self.repo.list_memories(include_inactive=True)))

        exported = self.repo.export_json()
        exported_ids = {memory["id"] for memory in exported["memories"]}
        self.assertEqual(created_ids, exported_ids)

    def test_pin_unpin_persistence_idempotency_and_audit_events(self) -> None:
        memory = self.repo.create_memory("用户偏好：个人 wiki 笔记默认写中文", "global")

        pinned = self.repo.pin_memory(memory.id)
        self.assertEqual("pinned", pinned.status)
        self.assertEqual([memory.id], [item.id for item in self.repo.get_pinned(scope="global")])

        pinned_again = self.repo.pin_memory(memory.id)
        self.assertEqual("pinned", pinned_again.status)

        unpinned = self.repo.unpin_memory(memory.id)
        self.assertEqual("active", unpinned.status)
        self.assertEqual([], self.repo.get_pinned(scope="global"))

        unpinned_again = self.repo.unpin_memory(memory.id)
        self.assertEqual("active", unpinned_again.status)

        events = [event.event_type for event in self.repo.list_events(memory.id)]
        self.assertEqual(["created", "pinned", "unpinned"], events)

        reopened = MemoryRepository(self.db_path)
        self.assertEqual("active", reopened.get_memory(memory.id).status)

    def test_pinned_retrieval_excludes_inactive_statuses(self) -> None:
        active = self.repo.create_memory("active pinned", "global", status="pinned")
        expired = self.repo.create_memory("expired pinned", "global", status="pinned")
        archived = self.repo.create_memory("archived pinned", "global", status="pinned")
        superseded = self.repo.create_memory("superseded pinned", "global", status="pinned")
        deleted = self.repo.create_memory("deleted pinned", "global", status="pinned")

        self.repo.update_memory(expired.id, {"status": "expired"})
        self.repo.update_memory(archived.id, {"status": "archived"})
        self.repo.update_memory(superseded.id, {"status": "superseded"})
        self.repo.soft_delete(deleted.id)

        self.assertEqual(
            [active.id], [memory.id for memory in self.repo.get_pinned(scope="global")]
        )
        with self.assertRaises(InvalidTransitionError):
            self.repo.pin_memory(expired.id)

    def test_initialize_creates_lookup_indexes(self) -> None:
        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        index_names = {row["name"] for row in rows}
        self.assertIn("idx_memories_scope_status_updated", index_names)
        self.assertIn("idx_memories_status_updated", index_names)
        self.assertIn("idx_memory_events_memory_id", index_names)

    def test_initialize_migrates_legacy_memory_rows_to_normalized_schema(self) -> None:
        legacy_path = Path(self.tmpdir.name) / "legacy.db"
        with closing(connect(legacy_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE memories (
                  id TEXT PRIMARY KEY,
                  content TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  status TEXT NOT NULL,
                  confidence REAL NOT NULL,
                  source_kind TEXT NOT NULL,
                  source_ref TEXT,
                  valid_from TEXT NOT NULL,
                  valid_to TEXT,
                  supersedes_id TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  tags TEXT NOT NULL DEFAULT '[]',
                  metadata TEXT NOT NULL DEFAULT '{}'
                );
                INSERT INTO memories (
                  id, content, kind, scope, status, confidence, source_kind, source_ref,
                  valid_from, created_at, updated_at, tags, metadata
                )
                VALUES (
                  'mem_legacy', 'Legacy transcript note', 'note', 'global', 'active', 1.0,
                  'import', 'legacy.jsonl', '2026-01-01T00:00:00Z',
                  '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', '[]', '{}'
                );
                """
            )
            connection.commit()

        migrated = MemoryRepository(legacy_path)
        migrated.initialize()

        memory = migrated.get_memory("mem_legacy")
        self.assertEqual("lam.memory.v1", memory.schema_version)
        self.assertEqual([], memory.entities)
        self.assertEqual("personal", memory.privacy)
        self.assertEqual([memory.id], [item.id for item in migrated.search("Legacy")])


if __name__ == "__main__":
    unittest.main()
