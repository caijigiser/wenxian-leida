"""生成中文库(知网/万方)专业检索式, 供用户手动到平台检索下载(合法途径)。

用法:
  python cnki_query.py [--domain A] [--all]
"""
from __future__ import annotations
import argparse
from wxl_common import load_config


def show(code: str, d: dict, since: int) -> None:
    print("=" * 78)
    print(f"领域 {code}: {d['name_zh']}")
    print("-" * 78)
    print("【中文关键词】", " · ".join(d["keywords_zh"]))
    print()
    print("【知网 CNKI 专业检索式】(高级检索 -> 专业检索, 粘贴; 再限年份>=%d, 按被引/相关排序)" % since)
    print(d["cnki_query"])
    print()
    print("【万方 专业检索式】")
    print(d["wanfang_query"])
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    since = cfg["settings"].get("since_year", 2016)
    if args.all or not args.domain:
        for code, d in cfg["domains"].items():
            show(code, d, since)
    else:
        show(args.domain.upper(), cfg["domains"][args.domain.upper()], since)
    print("=" * 78)
    print("提示: 知网/万方无合法自动化接口, 请手动检索; 下载后拖入 Zotero 即可, 之后照样接入分诊与 Obsidian 流程。")


if __name__ == "__main__":
    main()
