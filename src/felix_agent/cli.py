"""安装后的 felix-agent 命令，运行时不修改 sys.path。"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from felix_agent.agent import run_agent
from felix_agent.retrieval import index_documents, search
from felix_agent.storage import Store
from felix_agent.tools import CreateTicket, Tools


def approve(draft: CreateTicket) -> bool:
    print("\n请求创建工单；请核对以下完整内容：", file=sys.stderr)
    print(draft.model_dump_json(indent=2), file=sys.stderr)
    if not sys.stdin.isatty():
        print("非交互终端：拒绝写入。", file=sys.stderr)
        return False
    try:
        return input("输入 APPROVE 确认，其他输入均拒绝：") == "APPROVE"
    except EOFError:
        return False


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def positive_float(value: str) -> float:
    number = float(value)
    if not 0 < number < float("inf"):
        raise argparse.ArgumentTypeError("必须是有限正数")
    return number


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="知识库与人工审批工单实战环境")
    command.add_argument("--data-dir", type=Path, default=Path(".data"), help="本地数据目录")
    sub = command.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="检查环境，不输出凭据或访问模型服务")
    initialize = sub.add_parser("init", help="从 Markdown 文档重建检索索引，不删除工单")
    initialize.add_argument("--docs", type=Path, default=Path("knowledge"))
    query = sub.add_parser("search", help="直接检索，无需 API Key")
    query.add_argument("query")
    tickets = sub.add_parser("tickets", help="列出工单或查询一个 ID")
    tickets.add_argument("ticket_id", type=positive_int, nargs="?")
    create = sub.add_parser("create", help="直接体验人工审批与真实落库，无需模型")
    create.add_argument("--title", required=True)
    create.add_argument("--description", required=True)
    create.add_argument("--request-id", default=None, help="重复操作复用同一 ID，且内容必须相同")
    agent = sub.add_parser("run", help="调用真实模型，执行原生工具循环")
    agent.add_argument("prompt")
    agent.add_argument("--request-id", default=None, help="一个 ID 对应一个工单；重试复用")
    agent.add_argument("--max-steps", type=positive_int, default=8)
    agent.add_argument("--max-output-tokens", type=positive_int, default=1024)
    agent.add_argument(
        "--timeout", type=positive_float, default=30, help="每次模型 HTTP 请求超时秒数"
    )
    return command


def main() -> int:
    command = parser()
    args = command.parse_args()
    load_dotenv(Path.cwd() / ".env", override=False)
    if args.command == "doctor":
        with sqlite3.connect(":memory:") as connection:
            sqlite_ok = connection.execute("SELECT 1").fetchone()[0] == 1
        print(
            json.dumps(
                {
                    "python": sys.version.split()[0],
                    "sqlite": sqlite3.sqlite_version,
                    "sqlite_ok": sqlite_ok,
                    "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
                    "model_configured": bool(os.getenv("OPENAI_MODEL")),
                    "index_exists": (args.data_dir / "workspace.sqlite3").is_file(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "run":
        if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
            command.error("请在 .env 或环境变量中设置 OPENAI_API_KEY 和 OPENAI_MODEL")
    request_id = getattr(args, "request_id", None) or str(uuid4())
    try:
        with Store(args.data_dir / "workspace.sqlite3") as store:
            if args.command == "init":
                result = index_documents(store, args.docs)
            elif args.command == "search":
                result = {"matches": search(store, args.query)}
            elif args.command == "tickets":
                result = (
                    {"ticket": store.ticket(args.ticket_id)}
                    if args.ticket_id
                    else {"tickets": store.tickets()}
                )
            else:
                tools = Tools(store, request_id, approve)
                if args.command == "create":
                    result = tools.execute(
                        "create_ticket",
                        json.dumps(
                            {
                                "title": args.title,
                                "description": args.description,
                            }
                        ),
                    )
                    result["request_id"] = request_id
                else:
                    if not store.chunks():
                        command.error("知识库未初始化；请先运行 felix-agent init")
                    with OpenAI(
                        api_key=os.environ["OPENAI_API_KEY"],
                        base_url=os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
                        timeout=args.timeout,
                        max_retries=0,
                    ) as client:
                        result = run_agent(
                            client=client,
                            model=os.environ["OPENAI_MODEL"],
                            tools=tools,
                            prompt=args.prompt,
                            max_steps=args.max_steps,
                            max_output_tokens=args.max_output_tokens,
                            trace_path=args.data_dir / "traces" / f"{uuid4()}.jsonl",
                        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(
            "error" in result
            or result.get("status")
            in {
                "step_limit",
                "model_error",
                "local_error",
                "output_incomplete",
                "empty_response",
            }
        )
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"本地操作失败（{type(error).__name__}）：请检查路径、文档或数据。", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已取消。", file=sys.stderr)
        return 130
