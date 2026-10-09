"""文献雷达总编排: 对多个领域依次跑 检索 -> 去重 -> 下载OA -> (可选)写入Zotero,
并汇总成一个 triage 结果文件, 供 Claude 阅读生成分诊表。

用法示例:
  python radar.py --domains A,B --since 2020 --max 8 --dry-run          # 只检索+去重, 不写入(测试)
  python radar.py --domains A,B,C --since 2018 --import --attach          # 全流程并写入Zotero+挂OA附件

默认不写入 Zotero (安全); 加 --import 才写。加 --no-pdf 跳过 PDF 下载。
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from typing import List

from wxl_common import load_config, read_json, write_json

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(script: str, args: List[str]) -> int:
    cmd = [PY, os.path.join(HERE, script)] + args
    sys.stderr.write(f"\n$ {' '.join(cmd)}\n")
    return subprocess.call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", default="A,B,C")
    ap.add_argument("--since", type=int, default=None)
    ap.add_argument("--max", type=int, default=None, dest="maxn")
    ap.add_argument("--import", dest="do_import", action="store_true")
    ap.add_argument("--pdf", action="store_true",
                    help="下载OA全文PDF到暂存目录(默认不下; PDF靠本地Zotero『查找可用PDF』合法抓取)")
    ap.add_argument("--attach", action="store_true",
                    help="导入时附带OA直链附件, 由Zotero自行下载全文(推荐, 全自动)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    outdir = cfg["settings"].get("output_dir", ".")
    os.makedirs(outdir, exist_ok=True)
    domains = [d.strip().upper() for d in args.domains.split(",") if d.strip()]

    all_new: List[dict] = []
    for dom in domains:
        raw = os.path.join(outdir, f"results_{dom}.json")
        ded = os.path.join(outdir, f"results_{dom}_dedup.json")
        sargs = ["--domain", dom, "--out", raw]
        if args.since: sargs += ["--since", str(args.since)]
        if args.maxn: sargs += ["--max", str(args.maxn)]
        run("search.py", sargs)
        run("dedup.py", ["--in", raw, "--out", ded])

        if args.pdf and not args.dry_run:
            run("fetch_pdf.py", ["--in", ded, "--limit", "15"])

        if os.path.exists(ded):
            for r in read_json(ded)["records"]:
                r["domain"] = dom
                all_new.append(r)

    triage = os.path.join(outdir, "triage_results.json")
    write_json(triage, {"count": len(all_new), "records": all_new})
    print(f"\n[done] 汇总新增 {len(all_new)} 条 -> {triage}")

    # connector 写入 Zotero【当前选中分类】: 单领域直接导入; 多领域需分领域跑(中间切换选中分类)
    if args.do_import:
        if len(domains) == 1:
            iargs = ["--in", triage, "--domain", domains[0], "--limit", "999"]
            if args.dry_run: iargs.append("--dry-run")
            if args.attach: iargs.append("--attach")
            run("import_zotero.py", iargs)
        else:
            print("[提示] 多领域导入: connector 只写『当前选中分类』, 请按领域分别执行(先在 Zotero 选中对应分类):")
            for dom in domains:
                cname = cfg["domains"].get(dom, {}).get("collection", f"文献雷达-{dom}")
                extra = " --dry-run" if args.dry_run else ""
                print(f"  ({dom}) 选中「{cname}」后运行: python import_zotero.py --in {triage} --domain {dom}{extra}")

    print("下一步: Claude 读取 triage_results.json, 生成分诊表(中文摘要/创新点/相关性/推荐度), 你勾选精读项接入 Obsidian。")


if __name__ == "__main__":
    main()
