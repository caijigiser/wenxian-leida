---
description: 文献雷达·领域B (加 import 真实导入)
---
运行「文献雷达」wenxian-leida skill，**领域 B**。参数: $ARGUMENTS

- 参数含 `import` → 真实导入；否则先 dry-run 出分诊表，我确认后再导入。
- `cd ~\.claude\skills\wenxian-leida\scripts`
- dry-run：`python radar.py --domains B --since 2018 --max 12 --dry-run`
- import：**先提醒我在 Zotero 左侧选中领域 B 对应的「文献雷达-B …」分类**（分类名见 config/domains.json），再跑 `python radar.py --domains B --since 2018 --max 12 --import`（本地 connector 写入，免授权零弹窗不碰云端；脚本自动校验选中分类，不匹配会中止防写错）
- 读 `triage_results.json` 按 `references/TRIAGE-SCHEMA.md` 生成中文分诊表给我并保存到 `triage_md_dir`；我勾选精读项后接 `zotero-obsidian-bridge`（若已安装）。
- 全文：付费墙文献同步到本地后，在 Zotero 右键『查找可用PDF』用机构订阅合法抓取。
- 红线：不用盗版/账号密码；中文库用 `python cnki_query.py --domain B` 生成检索式让我手动跑。
