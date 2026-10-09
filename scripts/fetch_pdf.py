"""下载开放获取(OA)全文 PDF 到暂存目录。

策略(逐级降级):
  1. 记录里已有的 oa_url
  2. Unpaywall 按 DOI 查最佳 OA 位置 (需 email)
只下 OA; 付费墙文献跳过(交给 Zotero「查找可用PDF」用机构订阅合法抓取)。

用法:
  python fetch_pdf.py --in results_A_dedup.json [--limit 20] [--email you@x.org]
给每条记录加 pdf_path (成功时)。
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from typing import Any, Dict, Optional

from wxl_common import load_config, external_session, retry_get, read_json, write_json

UNPAYWALL = "https://api.unpaywall.org/v2/"


def safe_name(rec: Dict[str, Any]) -> str:
    base = rec.get("doi") or re.sub(r"[^A-Za-z0-9]+", "_", rec.get("title", "paper"))[:60]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base.replace("/", "_"))
    return (base or "paper")[:80] + ".pdf"


def unpaywall_url(sess, doi: str, email: str) -> Optional[str]:
    if not doi or not email:
        return None
    r = retry_get(sess, UNPAYWALL + doi, params={"email": email}, max_tries=2)
    if not r or r.status_code != 200:
        return None
    j = r.json()
    best = j.get("best_oa_location") or {}
    return best.get("url_for_pdf") or best.get("url")


def download(sess, url: str, dest: str) -> bool:
    try:
        r = sess.get(url, timeout=90, stream=True,
                     headers={"User-Agent": "Mozilla/5.0 (wenxian-leida)"})
        if r.status_code != 200:
            return False
        ct = r.headers.get("Content-Type", "")
        head = next(r.iter_content(1024), b"") or b""
        if "pdf" not in ct.lower() and not head.startswith(b"%PDF"):
            sys.stderr.write(f"[warn] 非PDF响应 ({ct}): {url[:70]}\n")
            return False
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(head)
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
        return os.path.getsize(dest) > 1024
    except Exception as e:
        sys.stderr.write(f"[warn] 下载失败 {url[:70]}: {e}\n")
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--email", default="researcher@example.org")
    args = ap.parse_args()

    cfg = load_config()
    pdf_dir = cfg["settings"]["staging_pdf_dir"]
    data = read_json(args.inp)
    sess = external_session()
    got = 0
    for rec in data["records"]:
        if got >= args.limit:
            break
        if not rec.get("is_oa") and not rec.get("oa_url"):
            continue
        url = rec.get("oa_url") or unpaywall_url(sess, rec.get("doi", ""), args.email)
        if not url:
            continue
        dest = os.path.join(pdf_dir, safe_name(rec))
        if os.path.exists(dest):
            rec["pdf_path"] = dest; got += 1; continue
        sys.stderr.write(f"[pdf] {rec.get('title','')[:50]} <- {url[:60]}\n")
        if download(sess, url, dest):
            rec["pdf_path"] = dest
            got += 1
    write_json(args.inp, data)
    print(f"[ok] 已下载/存在 OA PDF {got} 份 -> {pdf_dir}")


if __name__ == "__main__":
    main()
