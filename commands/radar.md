---
description: 文献雷达·通用 - 检索研究领域并导入Zotero (参数: 领域A/B/C可逗号组合; 加 import 则真实导入)
---
运行「文献雷达」wenxian-leida skill。参数: $ARGUMENTS

**解析参数**：
- 领域：参数中出现的 A/B/C（如 `A` 或 `A,B`）；未指定则默认 `A,B,C`。
- 模式：参数含 `import` → 真实导入 Zotero；否则先 dry-run 出分诊表给我看，确认后再导入。
- 可选：`since=2020`、`max=20` 覆盖默认（since 默认 2018，max 默认 12）。

**执行步骤**：
1. `cd ~\.claude\skills\wenxian-leida\scripts`
2. 检索+去重（+下载OA）：
   - dry-run 模式：`python radar.py --domains <领域> --since <年> --max <n> --dry-run`
   - import 模式：**先提醒我在 Zotero 左侧选中「文献雷达-X …」目标分类**，再跑 `python radar.py --domains <领域> --since <年> --max <n> --import`（本地 connector 写入，免授权零弹窗；脚本校验选中分类，不匹配中止）。**多领域**时 connector 只写当前选中分类，radar.py 会打印分领域命令，逐个领域"选分类→导入"。
3. 读 `output_dir/triage_results.json`（路径见 config/domains.json），按 `references/TRIAGE-SCHEMA.md` 生成**中文分诊表**（标题 | 年 | 领域 | 中文摘要 | 创新点 | 相关性 | 推荐度 | OA | DOI），按推荐度分组排序给我，并保存 Markdown 到 `triage_md_dir`。
4. 若为 dry-run：分诊表给我看后，**问我是否真实导入**；我确认后再跑 import 命令。
5. 付费墙文献（OA❌）提示我：本地同步后在 Zotero 里右键『查找可用PDF』用机构订阅合法抓取。
6. 我勾选要精读的论文后，调用 `zotero-obsidian-bridge` skill（若已安装）为它们在 `Sources/Papers/` 生成中文规范笔记。

**红线**：绝不使用任何盗版聚合平台或账号密码；知网/万方只生成检索式（`python cnki_query.py --domain <领域>`）供我手动检索。
