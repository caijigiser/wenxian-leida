# 📡 文献雷达 wenxian-leida

> **Claude Code skill**：自动扫描你研究领域的新论文 → 批量导入 Zotero → 生成中文分诊表 → 勾选后交接 Obsidian 做精读笔记。

把「手动检索 Web of Science / 知网 → 逐篇下载 → 导入 Zotero → 读摘要筛选」的重复劳动，压缩成**一条命令 + 一次勾选**。

作者实测：三个领域一次雷达扫描 **162 篇**论文自动入库 Zotero，分诊表直接落盘 Obsidian。

---

## ✨ 用起来什么样

在 Claude Code 对话里直接说：

> 帮我检索冻土路基方向的新文献，导入 Zotero，出个分诊表

或用 slash 命令（见 `commands/`）：

| 命令 | 作用 |
|---|---|
| `/radar-a` | 领域 A 雷达（先 dry-run 出分诊表，不写库） |
| `/radar-a import` | 真实导入 Zotero（先在 Zotero 左侧选中对应分类） |
| `/radar` | 通用版，参数自由组合领域：`/radar A,B import` |
| `/radar-b` `/radar-c` | 领域 B / C 专用 |

**产出**：中文分诊表（标题｜年份｜中文摘要｜创新点｜相关性｜推荐度｜OA｜DOI），按 必读/建议读/备选/跳过 分组，保存为带 frontmatter 的 Markdown 笔记，勾选精读名单后可直接交给 [zotero-obsidian-bridge] 生成规范精读笔记。

## 🔄 工作流

```
OpenAlex 检索（中英文检索式，polite pool 防限流）
   │
   ├─ 质量过滤：撤稿 / supplement / corrigendum / 灌水刊自动剔除
   │            预印本遇到正式发表版 → 自动升级替换
   ├─ 对照 Zotero 库去重（DOI + 强标题归一化，库里有的不再导入）
   │
   ▼
本地 Connector 写入 Zotero（免授权、零弹窗、不依赖云存储）
   │
   ▼
Claude 生成中文分诊表 → 落盘 Obsidian/Markdown
   │
   ▼
你勾选精读名单 → zotero-obsidian-bridge（可选）→ Sources/Papers 精读笔记

全文获取：Zotero 右键『查找可用 PDF』（OA + 你的机构订阅，合法通道）
中文核心：cnki_query.py 生成知网/万方专业检索式，手动检索
```

## 🛡️ 合规红线（设计原则，写进了 skill 本体）

- ❌ 不爬 Web of Science / 知网
- ❌ 不使用任何盗版聚合平台，**永不接收账号密码**
- ✅ 元数据来自 OpenAlex 公开 API（CC0）
- ✅ 付费墙文献只靠你的机构订阅合法获取
- ✅ 中文库只生成专业检索式，由你手动执行

## 📦 安装

**依赖**：Claude Code · Python 3.9+（`pip install requests`）· Zotero 7 桌面版（保持运行）

1. 把本仓库放到 `~/.claude/skills/wenxian-leida/`（Windows：`C:\Users\<你>\.claude\skills\wenxian-leida\`）
2. 把 `commands/` 里的 4 个 `.md` 复制到 `~/.claude/commands/`
3. 按 **[INSTALL.md](INSTALL.md)** 三步配置：
   - 新建 `config/local.json` 填你的邮箱和输出路径（此文件不进 git）
   - Zotero 里建 3 个分类（名字照抄 config）
   - 把 `config/domains.json` 的检索式换成**你自己的研究方向**

## 🧩 定制你的研究领域

所有领域定义都在 `config/domains.json`，每个领域包含：

- `openalex_queries` —— 实际下发的检索式（英文为主，可加中文，OpenAlex 收录中文 OA 期刊）
- `cnki_query` / `wanfang_query` —— 知网（SU= 语法）/ 万方（主题:）专业检索式
- `collection` —— 对应的 Zotero 分类名
- `keywords_en` / `keywords_zh` —— 供 Claude 理解和扩展检索

默认示例是冻土/公路路基方向（A 稳定性、B 遥感形变监测、C 风险机器学习），照葫芦画瓢换成你的领域即可，详见 `references/KEYWORDS.md`。

## 📁 目录结构

```
wenxian-leida/
├── SKILL.md               # skill 主文件（Claude 的操作手册）
├── INSTALL.md             # 安装配置说明
├── README.md
├── commands/              # slash 命令 → 复制到 ~/.claude/commands/
│   ├── radar.md           # 通用（参数组合领域）
│   ├── radar-a.md         # 领域 A 专用
│   ├── radar-b.md         # 领域 B 专用
│   └── radar-c.md         # 领域 C 专用
├── config/
│   └── domains.json       # ★ 领域/关键词/检索式（主要改这里）
├── scripts/
│   ├── radar.py           # 总编排：检索→去重→导入
│   ├── search.py          # OpenAlex 检索 + 质量过滤 + 去重
│   ├── dedup.py           # 对照 Zotero 库查重
│   ├── import_zotero.py   # Connector 写入（校验选中分类，防写错）
│   ├── cnki_query.py      # 知网/万方检索式生成
│   ├── compact.py         # 分诊素材压缩（省 token）
│   ├── fetch_pdf.py       # OA PDF 抓取（可选）
│   ├── preview.py         # 结果质量预览
│   ├── zotero_web.py      # Web API 客户端（可选通道）
│   ├── authorize.py       # 本地 API 授权（遗留备用）
│   └── wxl_common.py      # 公共库：配置/会话/重试/去重键
├── references/
│   ├── ZOTERO-INTEGRATION.md  # Zotero 三种写入通道实测对比
│   ├── OPENAPI.md             # OpenAlex/S2/Unpaywall 接口笔记
│   ├── TRIAGE-SCHEMA.md       # 分诊表 schema + 落盘规范
│   └── KEYWORDS.md            # 关键词/检索式修改指南
└── evals/                 # skill 触发测试语料
```

## ⚙️ 技术要点

- **网络健壮性**：默认直连 OpenAlex（中国大陆可直连）；连接被代理重置或持续 429 时自动切换直连↔系统代理，指数退避（`wxl_common.retry_get`）。填邮箱进 polite pool 后基本告别 429。
- **为什么用 Connector 而不是 Web API**：`POST /connector/saveItems` 免授权、即写即得、**不受 Zotero 免费云存储 300MB 限制**（云存储满时 Web API 写入会因同步停摆到不了本地——作者实测踩坑）。代价是条目只进「当前选中分类」，所以脚本会先校验你选中的分类对不对，防止写错地方。三种通道完整对比见 `references/ZOTERO-INTEGRATION.md`。
- **只导元数据，不堆附件**：默认不下载 PDF（省云存储）；要 OA 附件加 `--attach`，或导入后在 Zotero 里批量『查找可用 PDF』。

## ❓ FAQ

**Q：只导入元数据，那我读什么？**
A：导入后在 Zotero 里全选 → 右键『查找可用 PDF』，OA 文献 + 你机构的订阅全文会批量自动挂上。分诊阶段读中文摘要足够做筛选决策。

**Q：Zotero 云存储满了还能用吗？**
A：能。Connector 写入本地库，元数据同步免费无限量；只有附件占存储。

**Q：检索被 429 限流？**
A：`config/local.json` 里填你的常用邮箱（OpenAlex polite pool，不校验不发信）。

**Q：我的方向不是冻土？**
A：改 `config/domains.json` 的检索式即可，领域代码 A/B/C 也能换。skill 本体与具体领域解耦。

## 📄 数据来源与许可

文献元数据来自 [OpenAlex](https://openalex.org)（CC0 公共领域）。本 skill 供学术研究使用，请遵守所在机构与目标数据库的服务条款。
