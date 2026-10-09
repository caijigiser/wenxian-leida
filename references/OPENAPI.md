# 开放学术 API 参考

全部为合法开放接口，无需付费。外部调用走系统代理（clash）正常。

## OpenAlex（主检索）— 免 key

`GET https://api.openalex.org/works`

| 参数 | 说明 |
|---|---|
| `search` | 全文相关性检索词 |
| `filter` | 如 `from_publication_date:2018-01-01` |
| `per-page` | ≤ 200 |
| `select` | 只要需要的字段省流量：`id,doi,title,display_name,publication_year,cited_by_count,open_access,primary_location,abstract_inverted_index,authorships` |
| `mailto` | **填真实邮箱进「polite pool」**，限速大幅放宽（否则直连易 429）。在 `config/domains.json` 的 `settings.openalex_email` 填。邮箱不校验、不发信，仅用于限速分级。 |

- **摘要**是 `abstract_inverted_index`（词→位置数组），用 `wxl_common.reconstruct_abstract()` 还原。
- `open_access.oa_url` 常直接给 OA PDF 链接。
- `settings.query_delay_sec`（默认 1.0s）控制查询间隔，礼貌限速。

## 网络健壮性（本机实测，重要）

本机（中国大陆 + clash-verge）访问 OpenAlex 有两条通道，各有毛病：
- **直连**（绕过 clash）：可达、快，但**出口 IP 易被 429 限流**（尤其 CGNAT 共享 IP / 短时间多次请求）。
- **系统代理**（clash）：出口 IP 不同、不易 429，但**间歇性重置连接**（ProxyError 10054）。

对策（已写进 `wxl_common`）：
1. `external_session(use_proxy=False)` **默认直连**。
2. `retry_get` 遇到**连接错误**或**持续 429** 时**自动切换通道**（直连↔代理，最多切 2 次），哪个通用哪个。
3. **填真实 `openalex_email`** 进 polite pool 是减少 429 的最有效手段。
4. 结果有本地缓存文件（results_*.json），重跑不必重复检索。

## Semantic Scholar（补 TLDR / OA / 引用）— 可选，易 429

批量：`POST https://api.semanticscholar.org/graph/v1/paper/batch?fields=externalIds,tldr,openAccessPdf,citationCount,abstract`，body `{"ids":["DOI:10.xxxx/...", ...]}`（≤ 500/次）。

- **无 key 时极易 429**（共享池限流）。`search.py` 的 `enrich_s2` 已做退避；拿不到 TLDR 不影响主流程（中文摘要由 Claude 基于 abstract 生成）。
- 想要稳定 TLDR：申请免费 key（semantic scholar 官网），填进 `config/domains.json` 的 `settings.s2_api_key`，脚本会自动带 `x-api-key` 头。
- 单条检索：`GET /graph/v1/paper/search?query=...&fields=title,abstract,tldr,openAccessPdf,externalIds`。

## Unpaywall（按 DOI 找 OA）— 需 email

`GET https://api.unpaywall.org/v2/{DOI}?email=you@x.org` → `best_oa_location.url_for_pdf`。`fetch_pdf.py` 在记录无 oa_url 时用它兜底。

## CORE / arXiv（补充 OA 源）

- arXiv：`http://export.arxiv.org/api/query?search_query=all:...`（预印本，领域 B/C 的遥感/ML 常有）。
- CORE：需注册 key，聚合仓储 OA 全文。v1 未接入，需要时在 `fetch_pdf.py` 加。

## 排序/筛选建议

检索结果按 `(year, cited_by)` 降序（`search.py` 已做）。分诊时优先看：近 2–3 年 + 有 OA + 与你方向强相关。
