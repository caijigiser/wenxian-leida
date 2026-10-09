"""把检索结果写入 Zotero —— 本地 connector 版（免授权、零弹窗、不碰云端、不受存储配额影响）。

connector 会把条目写进 Zotero【当前选中的分类】。运行前请在 Zotero 左侧
选中目标分类（如「文献雷达-A 冻土路基稳定性」）。脚本会先读取并校验当前
选中分类: 与领域配置的分类名不一致时中止(--force 可强制), 防止写错地方。

用法:
  python import_zotero.py --in results_A_dedup.json [--domain A] [--limit 999]
                          [--dry-run] [--force]
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from wxl_common import load_config, local_session, read_json


def get_selected_collection(sess, base: str) -> Optional[Dict[str, Any]]:
    """读 Zotero 当前选中的分类/库 (connector 端点, POST)。"""
    try:
        r = sess.post(f"{base}/connector/getSelectedCollection",
                      data="{}", headers={"Content-Type": "application/json"}, timeout=15)
    except Exception as e:
        sys.stderr.write(f"[error] 连不上 Zotero ({e}); 请确认 Zotero 正在运行。\n")
        return None
    if r.status_code != 200:
        sys.stderr.write(f"[warn] getSelectedCollection HTTP {r.status_code}: {r.text[:120]}\n")
        return None
    try:
        return r.json()
    except ValueError:
        return None


def build_item(rec: Dict[str, Any], attach: bool = False) -> Dict[str, Any]:
    doi = rec.get("doi") or ""
    url = rec.get("oa_url") or (f"https://doi.org/{doi}" if doi else rec.get("openalex_id", ""))
    dom = (rec.get("matched_domain") or rec.get("domain") or "?")
    item: Dict[str, Any] = {
        "itemType": "journalArticle",
        "title": rec.get("title", "").strip(),
        "creators": [{"creatorType": "author", "name": a} for a in (rec.get("authors") or [])],
        "tags": [{"tag": "文献雷达"}, {"tag": f"domain-{dom}"}],
        "abstractNote": rec.get("abstract", ""),
        "url": url,
    }
    # --attach: 让 Zotero 自己下载 OA 全文并挂为附件(只对 oa_url 是直链 PDF 的有效)
    if attach and rec.get("oa_url"):
        item["attachments"] = [{"url": rec["oa_url"], "mimeType": "application/pdf",
                                "title": "Full Text PDF"}]
    if doi:
        item["DOI"] = doi
    if rec.get("venue"):
        item["publicationTitle"] = rec["venue"]
    if rec.get("year"):
        item["date"] = str(rec["year"])
    if rec.get("pdf_path"):
        item["extra"] = (item.get("extra", "") + f"\nLocal PDF: {rec['pdf_path']}").strip()
    return item


def save_batch(sess, base: str, items: List[Dict[str, Any]]) -> bool:
    payload = {"sessionID": str(uuid.uuid4()), "uri": "https://openalex.org", "items": items}
    try:
        r = sess.post(f"{base}/connector/saveItems", data=json.dumps(payload),
                      headers={"Content-Type": "application/json"}, timeout=90)
    except Exception as e:
        sys.stderr.write(f"[error] connector 写入失败: {e}\n")
        return False
    if r.status_code in (200, 201):
        return True
    sys.stderr.write(f"[error] saveItems HTTP {r.status_code}: {r.text[:200]}\n")
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--domain")
    ap.add_argument("--limit", type=int, default=999)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--attach", action="store_true",
                    help="为有OA直链的条目附带PDF附件, 由Zotero自行下载(付费墙条目仍靠『查找可用PDF』)")
    ap.add_argument("--force", action="store_true", help="分类不匹配也强制写入当前选中分类")
    args = ap.parse_args()

    cfg = load_config()
    base = cfg["settings"]["zotero"]["local_api"]
    data = read_json(args.inp)
    recs = [r for r in data["records"] if not r.get("in_library")]
    if args.domain:
        recs = [r for r in recs if (r.get("matched_domain") or r.get("domain", "")).upper() == args.domain.upper()]
    recs = recs[:args.limit]
    if not recs:
        print("[ok] 没有需要写入的新条目。"); return

    # 按领域分组
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in recs:
        dom = (r.get("matched_domain") or r.get("domain") or args.domain or "?").upper()
        groups.setdefault(dom, []).append(r)

    sess = local_session()
    sel = get_selected_collection(sess, base)
    sel_name = (sel or {}).get("name") or (sel or {}).get("libraryName") or "(读不到)"
    print(f"[info] Zotero 当前选中: 「{sel_name}」")

    if args.dry_run:
        for dom, rs in groups.items():
            d = cfg["domains"].get(dom, {})
            print(f"[dry-run] 领域 {dom} ({len(rs)} 条) 期望分类「{d.get('collection','?')}」, 将写入当前选中「{sel_name}」; 示例:")
            print(json.dumps(build_item(rs[0]), ensure_ascii=False, indent=2)[:400])
        return

    # 校验: 混合领域必须分领域跑; 单领域须与配置分类名一致(除非 --force)
    if len(groups) > 1 and not args.force:
        sys.exit(f"[error] 记录含多个领域 {list(groups.keys())}, 但 connector 只写『当前选中分类』。\n"
                 f"请按领域分别运行: python import_zotero.py --in {args.inp} --domain A (并在Zotero选中对应分类)")
    dom = next(iter(groups))
    expect = cfg["domains"].get(dom, {}).get("collection", "")
    if expect and sel_name.strip() != expect.strip() and not args.force:
        sys.exit(f"[error] 当前选中分类「{sel_name}」≠ 领域{dom}期望的「{expect}」。\n"
                 f"请先在 Zotero 左侧点选「{expect}」再运行; 或加 --force 强制写入当前选中分类。")

    items = [build_item(r, args.attach) for r in recs]
    ok = 0
    B = 20
    for i in range(0, len(items), B):
        if save_batch(sess, base, items[i:i + B]):
            ok += len(items[i:i + B])
        time.sleep(0.5)
    print(f"[ok] 已写入 Zotero {ok}/{len(items)} 条 -> 分类「{sel_name}」(每条带 domain-{dom} 标签)")
    print("提示: 付费墙文献请在 Zotero 里右键『查找可用PDF』用机构订阅抓取。")


if __name__ == "__main__":
    main()
