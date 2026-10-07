import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from felix_agent.retrieval import index_documents, search
from felix_agent.storage import Store
from felix_agent.tools import Tools

DRAFT = {"title": "邮件未送达", "description": "已检查垃圾邮件，仍未收到重置邮件。"}


def test_denied_approval_never_writes(tmp_path):
    with Store(tmp_path / "db.sqlite") as store:
        tools = Tools(store, "request-1", lambda draft: False)
        result = tools.execute("create_ticket", json.dumps(DRAFT))
        assert result == {"error": "approval_denied", "created": False}
        assert store.tickets() == []
        with pytest.raises(PermissionError):
            store.create_ticket(request_id="bypass", approved=False, **DRAFT)
        assert store.tickets() == []


@pytest.mark.parametrize(
    "name,payload",
    [
        ("create_ticket", {**DRAFT, "approved": True}),
        ("create_ticket", {**DRAFT, "title": "   "}),
        ("create_ticket", {"title": "缺少描述"}),
        ("get_ticket", {"ticket_id": True}),
        ("get_ticket", {"ticket_id": "1"}),
        ("shell", {"command": "cat .env"}),
    ],
)
def test_invalid_or_unknown_tools_fail_before_approval(tmp_path, name, payload):
    def forbidden_approval(draft):
        pytest.fail("非法输入不能触发审批")

    with Store(tmp_path / "db.sqlite") as store:
        result = Tools(store, "request-1", forbidden_approval).execute(name, json.dumps(payload))
        assert result["error"] in {"invalid_arguments", "unknown_tool"}
        assert store.tickets() == []


def test_replay_after_restart_and_content_conflict(tmp_path):
    path = tmp_path / "db.sqlite"
    with Store(path) as store:
        first = Tools(store, "stable-id", lambda draft: True).execute(
            "create_ticket", json.dumps(DRAFT)
        )["ticket"]
    with Store(path) as store:
        tools = Tools(store, "stable-id", lambda draft: True)
        replay = tools.execute("create_ticket", json.dumps(DRAFT))["ticket"]
        assert replay == first
        conflict = tools.execute("create_ticket", json.dumps({**DRAFT, "title": "不同内容"}))
        assert conflict["error"] == "idempotency_conflict"
        assert store.tickets() == [first]
        assert tools.execute("get_ticket", '{"ticket_id": 999}')["status"] == "not_found"


def test_concurrent_same_request_creates_one_ticket(tmp_path):
    path = tmp_path / "db.sqlite"
    with Store(path):
        pass

    def create(_):
        with Store(path) as store:
            return store.create_ticket(request_id="same", approved=True, **DRAFT)

    with ThreadPoolExecutor(max_workers=4) as workers:
        tickets = list(workers.map(create, range(4)))
    with Store(path) as store:
        assert store.tickets() == [tickets[0]]
        assert all(ticket == tickets[0] for ticket in tickets)


def test_chinese_retrieval_and_no_evidence(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "account.md").write_text("忘记密码：使用重置邮件。", encoding="utf-8")
    (docs / "tickets.md").write_text("工单必须确认后创建。", encoding="utf-8")
    with Store(tmp_path / "db.sqlite") as store:
        index_documents(store, docs)
        assert search(store, "忘记密码怎么办")[0]["source"] == "account.md"
        assert search(store, "量子纠缠实验") == []
        assert (
            Tools(store, "read", lambda draft: False).execute(
                "search_docs", '{"query": "量子纠缠实验"}'
            )["status"]
            == "no_evidence"
        )


def test_failed_reindex_preserves_existing_documents(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    outside = tmp_path / "private.md"
    outside.write_text("不得索引的外部文件", encoding="utf-8")
    with Store(tmp_path / "db.sqlite") as store:
        store.replace_chunks([("old.md", 1, "原有知识")])
        with pytest.raises(ValueError):
            index_documents(store, docs)
        (docs / "escape.md").symlink_to(outside)
        with pytest.raises(ValueError):
            index_documents(store, docs)
        assert store.chunks() == [{"source": "old.md", "chunk_id": 1, "content": "原有知识"}]
