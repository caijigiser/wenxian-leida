"""紧凑分诊素材: 每篇一行概览 + 按被引排序的前N篇附摘要, 省token。
用法: python compact.py <triage_results.json> [topN=20]
"""
import json
import sys

path = sys.argv[1]
topn = int(sys.argv[2]) if len(sys.argv) > 2 else 20
d = json.load(open(path, encoding="utf-8"))
recs = d["records"]
recs.sort(key=lambda r: (r.get("cited_by") or 0, r.get("year") or 0), reverse=True)
oa = sum(1 for r in recs if r.get("is_oa"))
doms = {}
for r in recs:
    dm = r.get("matched_domain") or r.get("domain") or "?"
    doms[dm] = doms.get(dm, 0) + 1
print(f"total={len(recs)} OA={oa} domains={doms}")
for i, r in enumerate(recs):
    dom = r.get("matched_domain") or r.get("domain") or "?"
    ven = (r.get("venue") or "")[:38]
    print(f"#{i+1} [{r.get('year')}] c={r.get('cited_by')} {'OA' if r.get('is_oa') else '--'} ({dom}) "
          f"{(r.get('title') or '')[:110]} | {ven} | {r.get('doi') or '-'}")
    if i < topn and r.get("abstract"):
        print(f"    ABS: {r['abstract'][:200]}")
