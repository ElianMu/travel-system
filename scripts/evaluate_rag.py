"""RAG 评估：输出召回命中率与引用覆盖率（对应 TDD §12.4）。

默认只评估检索，不调用 LLM、不联网。加 --llm 时额外调用 LLM，
统计答案正文是否按要求写出了期望的来源文件。

用法：python -m scripts.evaluate_rag [--top-k 5] [--llm]
"""
import argparse
import json
from pathlib import Path

from app.config import settings
from app.rag import generator
from app.rag.embedder import embed

embed(["预热"])  # 预热 Embedding 模型，规避原生库冲突

from app.rag.retriever import retrieve  # noqa: E402

EVAL_SET = Path(__file__).with_name("rag_eval_set.json")


def evaluate(top_k: int, use_llm: bool) -> None:
    samples = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    recall_hits = citation_hits = answer_hits = 0

    for sample in samples:
        query, expected = sample["query"], sample["expected"]
        hits = retrieve(query, top_k=top_k)
        recalled = expected in {h["source_file"] for h in hits}

        accepted = [h for h in hits if h["score"] >= settings.retrieve_min_score]
        cited = expected in {c["source_file"] for c in generator.build_citations(accepted)}

        recall_hits += recalled
        citation_hits += cited
        marker = "OK  " if recalled and cited else "MISS"
        print(f"{marker} {query} -> {[h['source_file'] for h in hits[:3]]}")

        if use_llm and accepted:
            answer_hits += expected in generator.generate(query, accepted).text

    total = len(samples)
    print(f"\n样本数：{total}，Top-K：{top_k}")
    print(f"召回命中率：{recall_hits / total:.1%}")
    print(f"引用覆盖率：{citation_hits / total:.1%}")
    if use_llm:
        print(f"答案正文引用率：{answer_hits / total:.1%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int, default=settings.retrieve_top_k)
    parser.add_argument("--llm", action="store_true", help="调用 LLM 统计答案正文的引用")
    args = parser.parse_args()
    evaluate(args.top_k, args.llm)
