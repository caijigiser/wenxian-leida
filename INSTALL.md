# 文献雷达 wenxian-leida 安装说明（新用户必读）

## 1. 安装

把 `wenxian-leida/` 整个文件夹放到 `~/.claude/skills/`（Windows: `C:\Users\<你>\.claude\skills\`），或 `git clone` 本仓库到该位置，重启 Claude Code。
slash 命令（可选）：把仓库 `commands/` 目录里的 `radar.md / radar-a.md / radar-b.md / radar-c.md` 复制到 `~/.claude/commands/`。

## 2. 依赖

- **Python 3.9+** 且装了 `requests`（`pip install requests`）
- **Zotero 桌面版正在运行**（本地 API 127.0.0.1:23119）
- 网络能直连 `api.openalex.org`（中国大陆通常可直连；若你的环境必须走代理，见 SKILL.md「网络健壮性」）

## 3. 三步配置

1. **新建 `config/local.json`**（个人配置，已被 .gitignore 排除，不会误传 git）：
   ```json
   {
     "openalex_email": "你的邮箱@example.com",
     "staging_pdf_dir": "C:/Users/<你>/Documents/wenxian-leida/pdfs",
     "output_dir": "C:/Users/<你>/Documents/wenxian-leida/runs",
     "triage_md_dir": "C:/Users/<你>/Documents/wenxian-leida/triage"
   }
   ```
   - `openalex_email` 重要（OpenAlex polite pool，否则易被 429 限流；不校验、不发信，仅用于限速分级）
   - `triage_md_dir` 建议指到你 Obsidian vault 里的笔记目录
   - 这些值会覆盖 `domains.json` 里的占位默认值
2. **建分类**：在 Zotero 里手动建 3 个分类（名字须与 config 里 `domains.X.collection` 一致）：
   - 文献雷达-A 冻土路基稳定性
   - 文献雷达-B 遥感LiDAR形变监测
   - 文献雷达-C 冻土风险与机器学习
3. **改成你的研究方向**（本 skill 默认是冻土/路基方向）：编辑 `config/domains.json` 的 `domains`，替换每个领域的 `openalex_queries`（英文+中文检索式）、`keywords_zh`、`cnki_query`、`wanfang_query`、`collection`。领域代码 A/B/C 可换成你自己的。

## 4. 使用

- 对话里直接说："帮我检索XX方向的新文献，导入Zotero，出个分诊表"
- 或用命令：`/radar-a`（先出分诊表）→ 确认后 `/radar-a import`（真实导入，**先在 Zotero 选中对应分类**）
- 导入后在 Zotero 全选条目 → 右键『查找可用 PDF』批量抓全文（OA + 你的机构订阅）

## 5. 注意

- 写入走本地 connector，**不依赖 Zotero 云同步**（云存储 300MB 满也不受影响）
- `settings.zotero.mode` 保持 `connector`；`web` 模式需要云端同步正常 + Web API key，一般不用
- 红线：本 skill 不爬 WoS/知网、不使用任何盗版渠道或账号密码；中文核心文献请用 `cnki_query.py` 生成的检索式手动检索
