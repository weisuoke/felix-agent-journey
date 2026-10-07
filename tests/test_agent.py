import json

import httpx
from openai import OpenAI

from felix_agent.agent import run_agent
from felix_agent.storage import Store
from felix_agent.tools import Tools


def tool_response():
    return {
        "id": "completion-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "create_ticket",
                                "arguments": json.dumps(
                                    {"title": "邮件未到", "description": "已检查垃圾邮件"}
                                ),
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
    }


def test_step_limit_blocks_pending_write(tmp_path):
    def approval(draft):
        raise AssertionError("步数耗尽后不能继续审批或写入")

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=tool_response()))
    with (
        Store(tmp_path / "db.sqlite") as store,
        OpenAI(
            api_key="test-only", max_retries=0, http_client=httpx.Client(transport=transport)
        ) as client,
    ):
        result = run_agent(
            client=client,
            model="test-model",
            tools=Tools(store, "budget", approval),
            prompt="创建工单",
            trace_path=tmp_path / "trace.jsonl",
            max_steps=1,
        )
        assert result["status"] == "step_limit"
        assert store.tickets() == []


def test_model_failure_after_write_preserves_outcome_and_hides_raw_error(tmp_path):
    replies = [
        httpx.Response(200, json=tool_response()),
        httpx.Response(
            503, json={"error": {"message": "private-response-secret", "type": "server"}}
        ),
    ]
    transport = httpx.MockTransport(lambda request: replies.pop(0))
    trace_path = tmp_path / "trace.jsonl"
    with (
        Store(tmp_path / "db.sqlite") as store,
        OpenAI(
            api_key="test-only", max_retries=0, http_client=httpx.Client(transport=transport)
        ) as client,
    ):
        tools = Tools(store, "stable", lambda draft: True)
        result = run_agent(
            client=client,
            model="test-model",
            tools=tools,
            prompt="创建工单",
            trace_path=trace_path,
        )
        assert result["status"] == "model_error"
        assert result["total_tokens"] is None
        first = store.tickets()[0]
        replay = tools.execute(
            "create_ticket", json.dumps({"title": "邮件未到", "description": "已检查垃圾邮件"})
        )["ticket"]
        assert replay == first
        assert store.tickets() == [first]
    assert "private-response-secret" not in trace_path.read_text(encoding="utf-8")


def test_output_truncation_is_not_success(tmp_path):
    response = tool_response()
    response["choices"][0] = {
        "index": 0,
        "finish_reason": "length",
        "message": {"role": "assistant", "content": "工单已"},
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=response))
    with (
        Store(tmp_path / "db.sqlite") as store,
        OpenAI(
            api_key="test-only", max_retries=0, http_client=httpx.Client(transport=transport)
        ) as client,
    ):
        result = run_agent(
            client=client,
            model="test-model",
            tools=Tools(store, "limit", lambda draft: True),
            prompt="创建工单",
            trace_path=tmp_path / "trace.jsonl",
        )
        assert result["status"] == "output_incomplete"
        assert store.tickets() == []
