"""文献检索: OpenAlex(主) + Semantic Scholar(补摘要/TLDR/引用)。

用法:
  python search.py --domain A [--since 2018] [--max 25] [--no-s2] [--out results_A.json]

输出: 规范化记录列表 (title/year/doi/cited_by/oa_url/abstract/source/venue/s2_tldr)
"""
from __future__ import annotations
import argparse
import sys
import time
from typing import Any, Dict, List

from wxl_common import (load_config, external_session, retry_get, reconstruct_abstract,
                        dedup_key, domain_records, write_json, quality_check, is_preprint,
                        norm_title_strong)

OPENALEX = "https://api.openalex.org/works"
S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_openalex(sess, query: str, since: int, per_query: int, email: str = "") -> List[Dict[str, Any]]:
    params = {
        "search": query,
        "per-page": str(per_query),
        "filter": f"from_publication_date:{since}-01-01",
        "select": "id,doi,title,display_name,publication_year,cited_by_count,open_access,primary_location,abstract_inverted_index,authorships",
        # 真实邮箱 -> OpenAlex polite pool, 大幅放宽限速(否则直连易 429)
        "mailto": email or "wenxian-leida@example.org",
    }
    r = retry_get(sess, OPENALEX, params=params)
    if not r or r.status_code != 200:
        sys.stderr.write(f"[warn] OpenAlex 失败 '{query}': {getattr(r,'status_code','?')}\n")
        return []
    out = []
    for w in r.json().get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        oa = w.get("open_access") or {}
        loc = (w.get("primary_location") or {})
        src = ((loc.get("source") or {}).get("display_name")) if loc else None
        authors = [a.get("author", {}).get("display_name") for a in (w.get("authorships") or [])[:6]]
        out.append({
            "title": w.get("display_name") or w.get("title") or "",
            "year": w.get("publication_year"),
            "doi": doi,
            "cited_by": w.get("cited_by_count", 0),
            "is_oa": bool(oa.get("is_oa")),
            "oa_url": oa.get("oa_url") or "",
            "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
            "venue": src or "",
            "authors": [a for a in authors if a],
            "source": "openalex",
            "openalex_id": w.get("id", ""),
        })
    return out


def enrich_s2(sess, records: List[Dict[str, Any]], api_key: str, limit_total: int) -> None:
    """用 S2 批量补 TLDR + openAccessPdf (按 DOI 匹配)。原地更新 records。"""
    dois = [r["doi"] for r in records if r.get("doi")][:limit_total]
    if not dois:
        return
    headers = {"x-api-key": api_key} if api_key else {}
    # S2 batch 端点
    url = "https://api.semanticscholar.org/graph/v1/paper/batch"
    params = {"fields": "externalIds,tldr,openAccessPdf,citationCount,abstract"}
    ids = [f"DOI:{d}" for d in dois]
    for chunk_start in range(0, len(ids), 50):
        chunk = ids[chunk_start:chunk_start + 50]
        try:
            r = sess.post(url, params=params, json={"ids": chunk}, headers=headers, timeout=60)
        except Exception as e:
            sys.stderr.write(f"[warn] S2 batch 网络错误: {e}\n"); continue
        if r.status_code == 429:
            sys.stderr.write("[warn] S2 429, 退避 5s\n"); time.sleep(5)
            try:
                r = sess.post(url, params=params, json={"ids": chunk}, headers=headers, timeout=60)
            except Exception:
                continue
        if r.status_code != 200:
            sys.stderr.write(f"[warn] S2 batch {r.status_code}\n"); continue
        by_doi = {}
        for p in r.json():
            if not p:
                continue
            ext = p.get("externalIds") or {}
            d = (ext.get("DOI") or "").lower()
            if d:
                by_doi[d] = p
        for rec in records:
            p = by_doi.get((rec.get("doi") or "").lower())
            if not p:
                continue
            tldr = (p.get("tldr") or {}).get("text")
            if tldr:
                rec["s2_tldr"] = tldr
            oa_pdf = (p.get("openAccessPdf") or {}).get("url")
            if oa_pdf and not rec.get("oa_url"):
                rec["oa_url"] = oa_pdf; rec["is_oa"] = True
            if not rec.get("abstract") and p.get("abstract"):
                rec["abstract"] = p["abstract"]
        time.sleep(1.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--since", type=int, default=None)
    ap.add_argument("--max", type=int, default=None, dest="maxn")
    ap.add_argument("--no-s2", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = load_config()
    d = domain_records(cfg, args.domain)
    st = cfg["settings"]
    since = args.since or st.get("since_year", 2016)
    per_q = args.maxn or st.get("max_per_query", 25)

    sess = external_session()
    email = st.get("openalex_email", "")
    qdelay = st.get("query_delay_sec", 1.0)
    vbl = st.get("venue_blocklist", [])   # 灌水期刊黑名单(中文OA源实测需要)
    tbl = st.get("title_blocklist", [])   # 低质标题特征(浅谈/刍议等)
    if not email:
        sys.stderr.write("[warn] 未配置 openalex_email, 直连易被 429 限流; 建议在 config 填真实邮箱进 polite pool\n")
    merged: Dict[str, Dict[str, Any]] = {}
    strong_map: Dict[str, str] = {}   # 强标题键 -> merged键, 抓预印本vs正式版重复
    filtered: Dict[str, int] = {"retracted": 0, "supplement": 0, "corrigendum": 0, "dup": 0}
    for q in d["openalex_queries"]:
        sys.stderr.write(f"[openalex] {q}\n")
        for rec in search_openalex(sess, q, since, per_q, email):
            keep, reason = quality_check(rec)
            if not keep:
                filtered[reason] = filtered.get(reason, 0) + 1
                sys.stderr.write(f"[filter] 跳过{reason}: {rec.get('title','')[:60]}\n")
                continue
            if any(b in (rec.get("venue") or "") for b in vbl) or any(b in (rec.get("title") or "") for b in tbl):
                filtered["blocklist"] = filtered.get("blocklist", 0) + 1
                continue
            k = dedup_key(rec)
            ks = "stitle:" + norm_title_strong(rec.get("title", ""))
            if k in merged or ks in strong_map:
                oldk = strong_map.get(ks)
                # 已有的是预印本、新的是正式版 -> 用正式版顶替
                if oldk and oldk in merged and merged[oldk].get("is_preprint") and not is_preprint(rec):
                    rec["matched_domain"] = args.domain.upper()
                    rec["matched_query"] = q
                    merged[oldk] = rec
                    sys.stderr.write(f"[upgrade] 预印本->正式版: {rec.get('title','')[:50]}\n")
                else:
                    filtered["dup"] += 1
                continue
            rec["matched_domain"] = args.domain.upper()
            rec["matched_query"] = q
            if is_preprint(rec):
                rec["is_preprint"] = True
            merged[k] = rec
            strong_map[ks] = k
        time.sleep(qdelay)  # OpenAlex 礼貌限速

    records = list(merged.values())
    records.sort(key=lambda r: (r.get("year") or 0, r.get("cited_by") or 0), reverse=True)

    if not args.no_s2 and st.get("s2_enabled", True):
        sys.stderr.write(f"[s2] 补充 TLDR/OA (共{len(records)}条)\n")
        enrich_s2(sess, records, st.get("s2_api_key", ""), limit_total=200)

    out = args.out or f"{st.get('output_dir','.')}/results_{args.domain.upper()}.json"
    write_json(out, {"domain": args.domain.upper(), "since": since, "count": len(records),
                     "filtered": filtered, "records": records})
    nfil = sum(filtered.values())
    print(f"[ok] {len(records)} 条 -> {out}" + (f" (质量过滤/去重 {nfil}: {filtered})" if nfil else ""))


if __name__ == "__main__":
    main()
