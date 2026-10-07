"""本地工单与文档存储；写入权限由工具边界和本层共同检查。"""

import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS chunks (
                source TEXT NOT NULL,
                chunk_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (source, chunk_id)
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
        """)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.connection.close()

    def replace_chunks(self, chunks: list[tuple[str, int, str]]) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM chunks")
            self.connection.executemany("INSERT INTO chunks VALUES (?, ?, ?)", chunks)

    def chunks(self) -> list[dict]:
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT source, chunk_id, content FROM chunks ORDER BY source, chunk_id"
            )
        ]

    def tickets(self) -> list[dict]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM tickets ORDER BY id")]

    def ticket(self, ticket_id: int) -> dict | None:
        row = self.connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None

    def create_ticket(
        self, *, request_id: str, title: str, description: str, approved: bool
    ) -> dict:
        if approved is not True:
            raise PermissionError("必须人工确认才能创建工单")
        # 唯一键和事务保证并发／重复请求不会重复落库。
        with self.connection:
            self.connection.execute(
                "INSERT INTO tickets (request_id, title, description) VALUES (?, ?, ?) "
                "ON CONFLICT(request_id) DO NOTHING",
                (request_id, title, description),
            )
            row = self.connection.execute(
                "SELECT * FROM tickets WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row["title"] != title or row["description"] != description:
                raise ValueError("同一 request_id 已用于不同工单内容")
            return dict(row)
