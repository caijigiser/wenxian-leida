---
name: wenxian-leida
description: 文献雷达(literature radar)——按研究领域自动检索中英文学术文献(OpenAlex开放API含中文OA源; 知网/万方生成专业检索式供手动检索)、去重、导入Zotero(connector本地写入分类, 可自动挂OA全文附件), 生成中文分诊表(摘要/创新点/相关性/推荐度), 勾选精读项交给zotero-obsidian-bridge建规范笔记。务必在用户说"检索文献/找论文/搜论文/查文献/我领域有没有新论文/最近有什么新文献/更新Zotero(指检索新文献入库)/扫一圈新论文/出分诊表/跑领域A、B或C/生成知网检索式/万方检索式/文献雷达/literature search"时使用, 或提到其研究方向(冻土/permafrost/路基/roadbed/沉降/形变监测/LiDAR/InSAR/青藏高原)并想找文献时使用, 即使没明说"文献雷达"。以下情况不用本skill：把已有论文整理成精读笔记、写综述/Knowledge整合、或写入Obsidian vault(用zotero-obsidian-bridge); 查询某条已知Zotero条目的元数据或全文(直接用zotero MCP工具); 参考PDF反向拆框架或仿写论文(用dashixiong-mofang); 检索专利(用patent-disclosure-skill); 论文润色、修代码、画流程图、清理Zotero库、讲解Zotero功能用法。红线：绝不连WoS/知网爬虫, 绝不用盗版渠道或账号密码; 付费墙文献靠Zotero「查找可用PDF」走机构订阅合法获取。
metadata:
  version: 1.0.0
---

# 文献雷达 wenxian-leida

按用户研究领域自动「检索 → 去重 → 导入 Zotero → 下 OA 全文 → 中文分诊 → 交接 Obsidian」。
把用户从「手动搜 WoS/知网 → 逐篇下载 → 手动导入」里解放出来。

## 三条不可逾越的红线

1. **绝不接收或使用任何账号密码**，绝不构建自动登录第三方聚合/盗版平台的流程。这类渠道侵权且不安全。
2. **付费墙文献不爬取**。合法途径是：建好 Zotero 条目后，让用户用 Zotero 自带「查找可用 PDF」经其**机构订阅/校园网代理**抓取；或走 OA/预印本/作者主页。
3. **知网/万方无合法自动接口**——只生成专业检索式，用户手动检索下载，再拖进 Zotero。

## 前置条件

- **Zotero 必须运行**（本地 API `127.0.0.1:23119`）。
- Python：`D:\Anaconda\python.exe`（3.9，已装 requests）。脚本在 `scripts/`，都从该目录运行或让 cwd 在此。
- **代理坑**：clash-verge 会拦截 localhost。脚本里 `local_session()` 已对 Zotero 强制绕过代理；手动 curl 测本地端点要加 `--noproxy "*"`。外部 API（OpenAlex 等）走系统代理正常。
- 配置在 `config/domains.json`：三领域关键词库、起始年份、输出目录、Zotero 分类名。

## 研究领域（可在 config 编辑）

- **A 冻土区路基稳定性**（青藏高原/G109）
- **B 遥感·LiDAR 形变监测与沉降参数提取**（含 InSAR/点云/ArcPy）
- **C 冻土工程风险评估与机器学习建模**

## 工作流

### 一键编排（推荐）

```bash
cd scripts
# 安全预演: 只检索+去重, 不写 Zotero
python radar.py --domains A,B,C --since 2018 --max 10 --dry-run
# 正式: 检索+去重+下OA全文+写入Zotero(带OA附件)
python radar.py --domains A,B,C --since 2018 --max 15 --import --attach
```

`radar.py` 产出 `output_dir/triage_results.json`（output_dir 见 config）。**默认不写 Zotero**，必须显式 `--import`。

**写入走本地 connector 通道**（免授权、零弹窗、不碰云端、不受 300MB 存储配额影响）：条目写进 Zotero **当前选中的分类**，每条带 `domain-A/B/C` 标签双保险。

> **一次性设置**：在 Zotero 手动建 3 个分类（右键 New Collection）：
> 「文献雷达-A 冻土路基稳定性」「文献雷达-B 遥感LiDAR形变监测」「文献雷达-C 冻土风险与机器学习」（名字在 config 里改）。
>
> **每次导入前**：先在 Zotero 左侧**点选目标分类**再跑 import。脚本会自动读取并校验当前选中分类，**与领域不匹配即中止**（防写错地方；`--force` 可强制）。
>
> **多领域一起导入**需按领域分别执行（中间切换选中分类），`radar.py` 会打印具体命令。
>
> （可选高级）云端同步正常且不想手动选分类的用户：`settings.zotero.mode` 改 `web` + Web API key 存 `config/zotero_webkey.txt`，可全自动建分类+分流，见 `references/ZOTERO-INTEGRATION.md`。注意 Zotero 免费云存储仅 300MB。

### 分步（需要精细控制时）

```bash
python search.py   --domain A --since 2018 --max 15 --out <out>/results_A.json   # OpenAlex+S2
python dedup.py    --in <out>/results_A.json                                       # 对照 Zotero 去重
python import_zotero.py --in <out>/results_A_dedup.json --domain A                 # connector写入(先在Zotero选中分类!)
python fetch_pdf.py --in <out>/results_A_dedup.json --limit 15                     # (可选)下OA全文到暂存目录
python cnki_query.py --domain A                                                    # 中文库检索式
python preview.py  <out>/results_A_dedup.json 5                                    # 看数据质量
```

> **PDF 获取三条路**：① 导入时加 `--attach` —— 有 OA 直链的条目由 Zotero 自动下载全文挂为附件（推荐，全自动）；② Zotero 里右键『查找可用 PDF』（可全选批量）—— OA + **机构订阅抓付费墙**，付费文献唯一合法途径，也用于补历史条目；③ `fetch_pdf.py`（或 `radar.py --pdf`）把 OA 下到暂存目录，不挂进 Zotero，仅要本地副本时用。

### Slash 命令（推荐日常用法）

已装用户级命令，直接输入即可：

| 命令 | 作用 |
|---|---|
| `/radar-a` `/radar-b` `/radar-c` | 分别跑领域 A / B / C |
| `/radar A,B` | 通用，任意领域组合；不带领域默认 A,B,C |
| 加 `import` | 如 `/radar-a import` → 真实导入（否则先 dry-run 出分诊表待确认） |
| 加 `since=2020 max=20` | 覆盖默认年份/数量 |

命令内部就是调本 skill 的 `radar.py`，并自动读结果生成中文分诊表、按你勾选交接 bridge。

### 分诊表（这一步是你 Claude 的核心工作，不是脚本）

读 `triage_results.json`，为每条记录用**中文**产出分诊表（保留英文术语/标题）。字段见 `references/TRIAGE-SCHEMA.md`，摘要来源优先级：`abstract` → `s2_tldr` → 标题推断（标注"仅标题"）。至少含：

| 标题(英) | 年 | 领域 | 中文一句话摘要 | 创新点 | 与本方向相关性 | 推荐度 | OA | zotero_key/DOI |
|---|---|---|---|---|---|---|---|---|

推荐度分档：**必读 / 建议读 / 备选 / 跳过**，并给一句理由。按推荐度排序，让用户一眼决定精读哪些。

**分诊表必须落盘**（对话里的表会丢）：每次生成后保存为 Markdown 到 `settings.triage_md_dir`（Obsidian vault 的 `Sources/Triage/`），文件名 `triage-YYYY-MM-DD-domain-X.md`，含 YAML frontmatter（type/domain/date/imported/oa/status）+ 分档表格 + 数据质量待办 + 原始数据路径。大列表用 `python compact.py triage_results.json 20` 省 token 地读素材。

### 交接 zotero-obsidian-bridge

用户勾选"精读"的条目后，调用 `zotero-obsidian-bridge` skill：按其规范在 `Sources/Papers/` 建中文规范笔记（含「中文摘要」「创新点」小节 + Evidence Record）。只把用户明确要精读的传下去，不要全量灌入。

## 全权委托还是逐步确认

首次运行或用户没指定时：**先 dry-run 出分诊表给用户看**，用户确认后再 `--import` 真正写入 Zotero。不要一上来就往库里塞几十条。

## 参考文档

- `references/ZOTERO-INTEGRATION.md` — connector 写入/授权删除/代理坑（实测结论）
- `references/OPENAPI.md` — OpenAlex / S2 / Unpaywall / CORE 端点与限流
- `references/TRIAGE-SCHEMA.md` — 分诊表字段 + 交接 bridge 的规则
- `references/KEYWORDS.md` — 如何增改领域与关键词

## 脚本清单

| 脚本 | 作用 |
|---|---|
| `wxl_common.py` | 配置/双会话(外部vs本地)/摘要重建/去重键/退避 |
| `search.py` | OpenAlex 主检索 + S2 批量补 TLDR/OA |
| `dedup.py` | 读 Zotero 现有库，按 DOI/标题去重 |
| `fetch_pdf.py` | 下载 OA 全文 PDF 到暂存目录 |
| `import_zotero.py` | **connector写入(默认)**：校验当前选中分类+批量导入（--dry-run/--force） |
| `zotero_web.py` | （可选）云端Web API客户端，mode=web时用（持久key，自动建分类分流） |
| `authorize.py` | （旧·本地授权key，已弃用，仅备用） |
| `cnki_query.py` | 生成知网/万方专业检索式 |
| `radar.py` | 总编排（多领域导入时打印分领域命令） |
| `preview.py` | 预览结果质量 |
| `compact.py` | 紧凑分诊素材（每篇一行+前N篇摘要，省token，分诊前必用） |
