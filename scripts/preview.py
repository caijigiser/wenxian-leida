"""预览检索结果 JSON 的质量。用法: python preview.py <results.json> [N]"""
import json, sys
path = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
d = json.load(open(path, encoding="utf-8"))
recs = d["records"]
print(f"domain={d['domain']} since={d['since']} total={d['count']}")
oa = sum(1 for r in recs if r.get("is_oa"))
tldr = sum(1 for r in recs if r.get("s2_tldr"))
absn = sum(1 for r in recs if r.get("abstract"))
print(f"OA全文={oa}  S2_TLDR={tldr}  有摘要={absn}\n")
for r in recs[:n]:
    print("=" * 80)
    print(f"[{r.get('year')}] cites={r.get('cited_by')} OA={r.get('is_oa')} doi={r.get('doi') or '-'}")
    print(f"  {r.get('title')}")
    print(f"  venue: {r.get('venue')}")
    if r.get("oa_url"):
        print(f"  oa_url: {r['oa_url'][:90]}")
    if r.get("s2_tldr"):
        print(f"  TLDR: {r['s2_tldr'][:160]}")
    if r.get("abstract"):
        print(f"  abs: {r['abstract'][:160]}")
