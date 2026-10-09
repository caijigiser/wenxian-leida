# 分诊表规范（Claude 产出，中文）

读 `output_dir/triage_results.json`，为每条记录生成分诊表。目的：让用户 30 秒内决定「精读 / 跳过」，而不是自己去啃英文摘要。

## 表字段

| 字段 | 来源 | 说明 |
|---|---|---|
| 标题 | `title` | 保留英文原标题 |
| 年 | `year` | |
| 领域 | `domain` | A/B/C |
| 中文一句话摘要 | `abstract`→`s2_tldr`→标题 | 用中文概括；术语保留英文。**只有标题时须标注「(仅标题, 无摘要)」** |
| 创新点 | 由摘要提炼 | 一句话点出方法/数据/结论的新意 |
| 相关性 | 对照用户方向 | 高/中/低 + 一句理由（为何与冻土路基/形变监测/风险建模相关） |
| 推荐度 | 综合判断 | **必读 / 建议读 / 备选 / 跳过** |
| OA | `is_oa` | ✅(有全文) / ❌(需机构订阅) |
| 定位 | `zotero_key` 或 `doi` | 便于在 Zotero 找到 |

## 摘要来源优先级

1. `abstract`（OpenAlex/S2 全文摘要）——最佳。
2. `s2_tldr`——次之（英文，需翻成中文）。
3. 都没有——**只能基于标题**，必须显式标注「(仅标题)」，并降低推荐度确定性，不要脑补摘要内容。

## 排序与呈现

- 按推荐度分组：必读 → 建议读 → 备选 → 跳过（跳过可折叠只列标题）。
- 每组内按年份倒序。
- 开头给一句总览：本次 X 领域共 N 篇新增，其中必读 a、建议读 b、OA 全文 c。

## 落盘保存（必须，勿只发对话）

对话中的分诊表会随会话丢失。每次生成后**必须**保存 Markdown：

- 位置：`settings.triage_md_dir`（config/domains.json），即 vault 的 `Research/permafrost-road/Sources/Triage/`
- 文件名：`triage-YYYY-MM-DD-domain-X.md`（同一天同领域重跑则覆盖/加序号）
- 结构：YAML frontmatter（type: triage / domain / date / source检索参数 / zotero_collection / imported / oa_fulltext / status: 待勾选精读）→ 总览 → 必读表 → 建议读表 → 备选一段 → 跳过一段 → 数据质量待办（supplement/重复预印本等）→ 下一步 checkbox → 原始数据 json 路径
- 用户勾选精读后，把该文件 status 改为「精读名单已定」并列出勾选清单

## 交接 zotero-obsidian-bridge 的规则

- **只把用户明确勾选「精读」的条目**交给 bridge，不要全量灌入 Obsidian。
- 按 bridge 规范：`Sources/Papers/{title-or-citekey}.md`，正文中文，含「中文摘要」「创新点」小节 + Evidence Record。
- 分诊表里「仅标题/仅摘要」的条目 → 进 bridge 的 `To-Read`，不得支撑 `Knowledge/` 结论（遵循 bridge 的 Claim Promotion Gate）。
- 用户勾选后再触发 bridge；bridge 负责建笔记、更新 registry/index/daily。

## 推荐度判据（结合用户方向）

- **必读**：直接命中冻土路基稳定性/形变监测方法/风险建模，且近 3 年 + 高相关或有 OA 全文。
- **建议读**：方法可迁移（如新 InSAR 时序法、新点云形变算法）或强相关综述。
- **备选**：边缘相关或较旧但被引高（奠基性）。
- **跳过**：主题偏离（如纯铁路轨道、非冻土区、纯材料）。
