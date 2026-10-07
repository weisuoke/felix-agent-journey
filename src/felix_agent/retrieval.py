"""小语料 BM25 检索：英文词、中文二元组；无模型或向量服务依赖。"""

import math
import re
from collections import Counter
from pathlib import Path

from felix_agent.storage import Store


def tokens(text: str) -> list[str]:
    result = re.findall(r"[a-z0-9_]+", text.lower())
    for phrase in re.findall(r"[\u4e00-\u9fff]+", text):
        result.extend(phrase[i : i + 2] for i in range(len(phrase) - 1))
        if len(phrase) == 1:
            result.append(phrase)
    return result


def index_documents(store: Store, directory: Path) -> dict:
    root = directory.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("文档路径必须是目录")
    chunks = []
    files = 0
    for path in sorted(root.rglob("*.md")):
        if not path.resolve().is_relative_to(root):
            raise ValueError("文档符号链接不能指向目录之外")
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        files += 1
        for chunk_id, start in enumerate(range(0, len(text), 850), 1):
            content = text[start : start + 1000]
            chunks.append((path.relative_to(root).as_posix(), chunk_id, content))
    if not chunks:
        raise ValueError("目录中没有非空 Markdown 文档；原索引保留")
    store.replace_chunks(chunks)
    return {"documents": files, "chunks": len(chunks)}


def search(store: Store, query: str, *, limit: int = 5) -> list[dict]:
    query_terms = set(tokens(query))
    chunks = store.chunks()
    if not query_terms or not chunks:
        return []
    frequencies = [Counter(tokens(chunk["content"])) for chunk in chunks]
    lengths = [sum(frequency.values()) for frequency in frequencies]
    average_length = sum(lengths) / len(lengths) or 1
    document_frequency = Counter(term for frequency in frequencies for term in frequency)
    scored = []
    for chunk, frequency, length in zip(chunks, frequencies, lengths, strict=True):
        score = 0.0
        for term in query_terms:
            count = frequency[term]
            if not count:
                continue
            df = document_frequency[term]
            idf = math.log(1 + (len(chunks) - df + 0.5) / (df + 0.5))
            score += idf * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * length / average_length))
        if score:
            scored.append({**chunk, "score": round(score, 6)})
    return sorted(scored, key=lambda chunk: (-chunk["score"], chunk["source"], chunk["chunk_id"]))[
        :limit
    ]
