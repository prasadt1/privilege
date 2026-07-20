"""SQLite vault. Raw documents and mappings are local-only data.

The OpenAI boundary starts above this module: only sanitized payloads may leave
the device. Ledger and receipt rows are application data, never log output.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any
from uuid import uuid4

from .policy import EngagementPolicy


DEFAULT_DB_PATH = Path.home() / ".privilege" / "vault.sqlite3"


class UnknownEngagementError(ValueError):
    """Raised when an operation references no known engagement."""


class UnknownDocumentError(ValueError):
    """Raised when an operation references no known document."""


@dataclass(frozen=True)
class Engagement:
    id: str
    name: str
    policy: EngagementPolicy
    created_at: str


@dataclass(frozen=True)
class Document:
    id: str
    engagement_id: str
    title: str
    raw_text: str
    created_at: str


class VaultStore:
    """Small SQLite repository for one local Privilege vault."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False lets the threaded local HTTP viewer reuse one
        # connection. Writes are serialized by _lock. This vault is single
        # operator and single process by design; it is not a shared server.
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self._connection.close()

    def _write(self, sql: str, params: tuple[Any, ...]) -> None:
        """Execute and commit one statement under the write lock."""
        with self._lock:
            self._connection.execute(sql, params)
            self._connection.commit()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS engagements (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, policy_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, engagement_id TEXT NOT NULL, title TEXT NOT NULL,
                raw_text TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY (engagement_id) REFERENCES engagements(id)
            );
            CREATE TABLE IF NOT EXISTS mappings (
                engagement_id TEXT NOT NULL, real_value TEXT NOT NULL, placeholder TEXT NOT NULL,
                PRIMARY KEY (engagement_id, real_value),
                FOREIGN KEY (engagement_id) REFERENCES engagements(id)
            );
            CREATE TABLE IF NOT EXISTS ledger (
                id TEXT PRIMARY KEY, engagement_id TEXT NOT NULL, destination TEXT NOT NULL,
                payload TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY (engagement_id) REFERENCES engagements(id)
            );
            CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY, engagement_id TEXT NOT NULL, decision TEXT NOT NULL,
                payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY (engagement_id) REFERENCES engagements(id)
            );
            """
        )
        self._connection.commit()

    def create_engagement(self, name: str, policy: EngagementPolicy | dict[str, Any]) -> str:
        policy_object = policy if isinstance(policy, EngagementPolicy) else EngagementPolicy.from_dict(policy)
        engagement_id = self._new_id("eng")
        self._write(
            "INSERT INTO engagements VALUES (?, ?, ?, ?)",
            (engagement_id, name, json.dumps(policy_object.to_dict()), self._now()),
        )
        return engagement_id

    def get_engagement(self, engagement_id: str) -> Engagement:
        row = self._connection.execute("SELECT * FROM engagements WHERE id = ?", (engagement_id,)).fetchone()
        if row is None:
            raise UnknownEngagementError(f"unknown engagement id: {engagement_id}")
        return Engagement(row["id"], row["name"], EngagementPolicy.from_dict(json.loads(row["policy_json"])), row["created_at"])

    def import_document(self, engagement_id: str, title: str, raw_text: str) -> str:
        self.get_engagement(engagement_id)
        document_id = self._new_id("doc")
        self._write(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
            (document_id, engagement_id, title, raw_text, self._now()),
        )
        return document_id

    def get_document(self, document_id: str) -> Document:
        row = self._connection.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            raise UnknownDocumentError(f"unknown document id: {document_id}")
        return Document(row["id"], row["engagement_id"], row["title"], row["raw_text"], row["created_at"])

    def list_documents(self, engagement_id: str) -> list[dict[str, str]]:
        """List local document metadata without returning raw document text."""
        self.get_engagement(engagement_id)
        rows = self._connection.execute(
            "SELECT id, engagement_id, title, created_at FROM documents WHERE engagement_id = ? ORDER BY created_at, id",
            (engagement_id,),
        )
        return [dict(row) for row in rows]

    def upsert_mapping(self, engagement_id: str, real_value: str, placeholder: str) -> None:
        self.get_engagement(engagement_id)
        self._write(
            "INSERT INTO mappings VALUES (?, ?, ?) ON CONFLICT(engagement_id, real_value) DO UPDATE SET placeholder = excluded.placeholder",
            (engagement_id, real_value, placeholder),
        )

    def get_mappings(self, engagement_id: str) -> dict[str, str]:
        self.get_engagement(engagement_id)
        rows = self._connection.execute(
            "SELECT real_value, placeholder FROM mappings WHERE engagement_id = ?", (engagement_id,)
        )
        return {row["real_value"]: row["placeholder"] for row in rows}

    def append_ledger(self, engagement_id: str, destination: str, payload: str) -> str:
        self.get_engagement(engagement_id)
        entry_id = self._new_id("led")
        self._write(
            "INSERT INTO ledger VALUES (?, ?, ?, ?, ?)",
            (entry_id, engagement_id, destination, payload, self._now()),
        )
        return entry_id

    def list_ledger(self, engagement_id: str, destination: str | None = None) -> list[dict[str, str]]:
        self.get_engagement(engagement_id)
        query = "SELECT * FROM ledger WHERE engagement_id = ?"
        params: tuple[str, ...] = (engagement_id,)
        if destination is not None:
            query += " AND destination = ?"
            params += (destination,)
        query += " ORDER BY created_at, id"
        return [dict(row) for row in self._connection.execute(query, params)]

    def save_receipt(self, engagement_id: str, decision: str, payload_json: dict[str, Any] | str) -> str:
        self.get_engagement(engagement_id)
        receipt_id = self._new_id("rcpt")
        payload = payload_json if isinstance(payload_json, str) else json.dumps(payload_json)
        self._write(
            "INSERT INTO receipts VALUES (?, ?, ?, ?, ?)",
            (receipt_id, engagement_id, decision, payload, self._now()),
        )
        return receipt_id

    def get_receipt(self, receipt_id: str) -> dict[str, str]:
        row = self._connection.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown receipt id: {receipt_id}")
        return dict(row)

    def list_receipts(self, engagement_id: str) -> list[dict[str, str]]:
        self.get_engagement(engagement_id)
        rows = self._connection.execute(
            "SELECT * FROM receipts WHERE engagement_id = ? ORDER BY created_at DESC, id DESC",
            (engagement_id,),
        )
        return [dict(row) for row in rows]

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()


Store = VaultStore
