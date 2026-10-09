# Zotero 集成（实测结论）

## ⭐ 主通道 = 本地 connector（当前采用：免授权、零弹窗、不碰云端）

`import_zotero.py` 默认走 `POST /connector/saveItems`（实测 201）：
- **无需任何 key/授权**，条目立即写进本地 Zotero，不受 300MB 云存储配额影响，离线可用，最利于 skill 推广。
- **写入位置 = Zotero 当前选中的分类**（saveItems 不接受 collectionKey）。故流程为：一次性手动建好「文献雷达-A/B/C」分类 → 每次导入前选中目标分类 → 跑 import。
- 脚本会先 `POST /connector/getSelectedCollection` 读当前选中分类并**校验与领域配置一致，不一致即中止**（`--force` 强制），防止写错。
- 多领域混合记录必须分领域跑（每组各自选分类）。
- 每条带 `domain-X` + `文献雷达` 标签，即使进错分类也能按标签找回。

## 可选通道 = 云端 Web API（`settings.zotero.mode: "web"`）

适合云端同步正常、想全自动建分类+分流的用户。⚠️ 前提：Zotero 免费云存储仅 300MB，**存储满会导致同步停摆、云端写入到不了本地**（本机实测踩过此坑）。本地授权 key（`/api/local/authorize`）秒级过期，批量写不可用，勿走那条路。

- **一次性设置**：`zotero.org/settings/keys` 建 private key（勾 Allow library access + **Read/Write**）→ 存 `config/zotero_webkey.txt`；`settings.zotero.user_id` 填你自己的数字 userID（同页面可见；建议写在 `config/local.json`，不进 git）。
- **请求头**：`Zotero-API-Key: <key>`、`Zotero-API-Version: 3`；写操作加 `If-Unmodified-Since-Version: <库版本>`（从任意 GET 的 `Last-Modified-Version` 头拿，每次写后递增）。
- **端点**：`/users/{id}/items`、`/users/{id}/collections`。
- **建条目**：`POST /users/{id}/items`，body 用索引对象 `{"0":{itemdata},"1":{...}}`；响应 `{"successful":{"0":{"key","version"}},"failed":{}}`。
- **建分类**：`POST /users/{id}/collections`，body `{"0":{"name":"..."}}`。
- **删除/改**：`DELETE/PATCH`，同样带 key + 版本头（持久 key 可直接删，无需弹窗）。
- **去重读库**：`GET /users/{id}/items?itemType=-attachment -note&limit=100&start=N` 分页，取 `data.DOI`/`data.title`。
- **同步**：写入云端后，本地 Zotero 需开启同步才会看到；去重也读云端，保证一致、不重复导入。
- 实现见 `scripts/zotero_web.py`（`ZoteroWeb` 类，含直连↔代理通道兜底）。

---

## 附：本地 API（旧方案，保留作背景/兜底）

### 通道一览

| 操作 | 端点 | 授权 | 实测 |
|---|---|---|---|
| 读条目/去重 | `GET /api/users/0/items` | 免授权 | ✅ 200 |
| **创建条目** | `POST /connector/saveItems` | **免授权** | ✅ **201** |
| 删除/改条目 | `DELETE|PATCH /api/users/0/items/{key}` | 需本地授权 key | 401 未授权 |
| 取授权 key | `POST /api/local/authorize` (body 需 `appName`) | 用户在弹窗点允许 | 428/400 已探明参数 |

## 代理坑（重要）

clash-verge 系统代理会拦截 `127.0.0.1`，导致「连接被意外关闭」。
- 脚本：`wxl_common.local_session()` 已设 `trust_env=False` + `proxies={'http':None,'https':None}`。
- 手动 curl：加 `--noproxy "*"`。
- PowerShell 原生：用 `HttpWebRequest` 并设 `$req.Proxy=$null`。

## 主力写入通道 = 授权本地 API（可建分类+按领域分流）

`import_zotero.py` 用这条。需一次性授权 key（见下「删除/管理」的授权流程）。

- **建/复用分类**：`GET /api/users/0/collections` 按 name 查；没有则 `POST /api/users/0/collections`，**body 必须是 JSON 数组** `[{"name":"文献雷达-A …"}]`。
- **建条目进分类**：`POST /api/users/0/items`，body 数组 `[{ ...itemdata, "collections":["<collKey>"] }]`。
- **必带头**：`Zotero-Server-ID`（任意 GET 响应头拿）、`Zotero-API-Key`（授权 key）、写操作加 `If-Unmodified-Since-Version: <当前库版本>`。
- **版本递增**：每次成功写返回新的 `Last-Modified-Version`，下一次写要用它，否则 412。
- 响应体 `{"successful":{"0":{"key":..,"version":..}}, "failed":{..}}`。

### key 短时效（实测坑）

`/api/local/authorize` 返回 `{"key":..,"remember":false}`——即使请求带 `remember:true` 也返回 false，key **短时效（约 1 分钟量级）**。对策（已写进 `import_zotero.py`）：
- 写入阶段**开头一次性校验 key**（`ensure_authed`），失效才弹一次窗；
- 之后**一口气批量写完**（本地写入每条 ~0.1s，30 条几秒，一个 key 有效期够）；
- 万一中途 401，`write()` 自动重授权并重试一次。
- 结论：正常每轮 `--import` **最多弹 1 次**授权窗。想要彻底免弹窗，可改用 Zotero **Web API key**（zotero.org/settings/keys，持久不过期，但走云端同步）。

## 免授权备用通道 = connector（只能进当前选中分类）

`POST http://127.0.0.1:23119/connector/saveItems`，Content-Type: application/json：

```json
{
  "sessionID": "<uuid>",
  "uri": "https://openalex.org",
  "items": [ { "itemType": "journalArticle", "title": "...", "creators": [{"creatorType":"author","name":"..."}],
               "DOI": "...", "url": "...", "abstractNote": "...", "publicationTitle": "...", "date": "2024",
               "tags": [{"tag":"文献雷达"}],
               "attachments": [{"url":"<oa_pdf_url>","mimeType":"application/pdf","title":"Full Text PDF"}] } ]
}
```

- 返回 201 即成功。**条目进入 Zotero 当前选中的分类**（saveItems 不接受 collectionKey）。
  → 运行前让用户在 Zotero 左侧选中目标分类（如「文献雷达-Inbox」）。
- `attachments[].url` 让 Zotero 自己去下 PDF；不想让脚本下 PDF 时，用这个即可。
- 建议每批 ≤ 20 条，批间稍等。

## 删除/管理（需一次性授权）

去重删除、移动分类、改条目需要本地授权 key：

1. 任意 GET 响应头里取 `Zotero-Server-ID`。
2. `POST /api/local/authorize`，头带 `Zotero-Server-ID`，body `{"appName":"wenxian-leida"}` → Zotero 弹授权框，用户点允许后返回 API key。
3. 之后 `DELETE /api/users/0/items/{key}`，头带 `Zotero-Server-ID`、`If-Unmodified-Since-Version: <version>`、以及授权 key。

v1 不需要删除能力（去重是只读的），故默认不走授权。若将来要「清理误入库」再启用。

## 去重键

优先 DOI（去掉 `https://doi.org/` 前缀、小写）；无 DOI 用规范化标题（去标点空格、小写、保留中文）。`dedup.py` 两键都建，命中任一即视为已收录。

## 付费墙文献

不爬取。建好条目后提示用户：Zotero 里右键条目 →「查找可用 PDF」，它会经用户机构订阅/校园网合法抓取。
