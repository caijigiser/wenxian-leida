"""去重: 读取 Zotero 现有库 (本地 API, 只读免授权), 标记已收录记录。

用法:
  python dedup.py --in results_A.json [--out results_A_dedup.json]

给每条记录加字段:
  in_library: true/false
  zotero_key: 已存在时的 key
输出仅保留 in_library=false 的新记录 (加 --keep-all 则全部保留)。
"""
from __future__ import annotations
import argparse
import sys
from typing import Any, Dict, List, Set

from wxl_common import load_config, local_session, norm_title, norm_title_strong, read_json, write_json
import zotero_web


def fetch_existing_web() -> Dict[str, str]:
    """走云端 Web API 读全库(与写入端一致, 避免刚导入未同步导致重复)。"""
    return zotero_web.ZoteroWeb().existing_dedup_keys()


def fetch_existing(sess, base: str) -> Dict[str, str]:
    """返回 {dedup_key: zotero_key}, 覆盖 DOI 与规范化标题两种键。"""
    keys: Dict[str, str] = {}
    start = 0
    limit = 100
    while True:
        url = f"{base}/api/users/0/items"
        params = {"limit": str(limit), "start": str(start), "format": "json",
                  "itemType": "-attachment -note"}
        try:
            r = sess.get(url, params=params, timeout=40)
        except Exception as e:
            sys.stderr.write(f"[warn] 读取 Zotero 失败 (start={start}): {e}\n")
            break
        if r.status_code != 200:
            sys.stderr.write(f"[warn] Zotero GET {r.status_code}; Zotero 是否在运行?\n")
            break
        batch = r.json()
        if not batch:
            break
        for it in batch:
            k = it.get("key", "")
            data = it.get("data", it)
            doi = (data.get("DOI") or "").strip().lower()
            title = data.get("title") or ""
            if doi:
                keys["doi:" + doi.replace("https://doi.org/", "")] = k
            if title:
                keys["title:" + norm_title(title)] = k
                keys["stitle:" + norm_title_strong(title)] = k
        if len(batch) < limit:
            break
        start += limit
    return keys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--keep-all", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    base = cfg["settings"]["zotero"]["local_api"]
    data = read_json(args.inp)
    recs: List[Dict[str, Any]] = data["records"]

    use_web = cfg["settings"]["zotero"].get("mode") == "web" and zotero_web.load_webkey()
    if use_web:
        existing = fetch_existing_web()
        src = "云端Web API"
    else:
        existing = fetch_existing(local_session(), base)
        src = "本地API"
    sys.stderr.write(f"[dedup] Zotero 现有条目键 {len(existing)} 个 (来源: {src})\n")

    new_recs = []
    dup = 0
    for r in recs:
        dk = None
        doi = (r.get("doi") or "").strip().lower()
        if doi:
            dk = "doi:" + doi.replace("https://doi.org/", "")
        tk = "title:" + norm_title(r.get("title", ""))
        sk = "stitle:" + norm_title_strong(r.get("title", ""))
        hit = existing.get(dk) if dk else None
        if not hit:
            hit = existing.get(tk) or existing.get(sk)
        if hit:
            r["in_library"] = True
            r["zotero_key"] = hit
            dup += 1
        else:
            r["in_library"] = False
        if args.keep_all or not r["in_library"]:
            new_recs.append(r)

    out = args.out or args.inp.replace(".json", "_dedup.json")
    write_json(out, {"domain": data.get("domain"), "since": data.get("since"),
                     "count": len(new_recs), "duplicates_skipped": dup, "records": new_recs})
    print(f"[ok] 新增 {len(new_recs)} 条 (跳过已收录 {dup} 条) -> {out}")


if __name__ == "__main__":
    main()
