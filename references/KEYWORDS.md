# 领域与关键词维护

所有检索词集中在 `config/domains.json`。改这个文件即可扩展/收窄方向，不用动代码。

## 结构

```jsonc
"domains": {
  "A": {
    "name_zh": "冻土区路基稳定性",
    "openalex_queries": [ "permafrost subgrade stability Qinghai-Tibet", ... ],  // ← 实际下发检索的语句
    "keywords_en": [...],       // 记录/展示用
    "keywords_zh": [...],       // 中文库关键词
    "cnki_query": "...",        // 知网专业检索式(手动用)
    "wanfang_query": "..."      // 万方专业检索式(手动用)
  }
}
```

## 调优建议

- **`openalex_queries` 最关键**：每条是一个独立检索式，结果自动合并去重。想更全 → 加同义表达（roadbed/subgrade/embankment、deformation/settlement/subsidence）；想更准 → 加限定词（Qinghai-Tibet、permafrost）。
- 检索太宽泛/噪声多：把泛词组拆细，或加地域/方法限定。
- 检索漏了重要文献：补该文献标题里的核心词组进 queries。
- `settings.since_year` 控制起始年；`max_per_query` 控制每条检索式取前 N。
- 新增领域：复制一个 A/B/C 块改成 "D"，`radar.py --domains A,B,C,D` 即可用。

## 当前三领域

- **A 冻土区路基稳定性**：permafrost · subgrade/roadbed stability · Qinghai-Tibet · thaw settlement · thermokarst · freeze-thaw · thermal regime · active layer · climate warming
- **B 遥感·LiDAR 形变监测**：LiDAR · point cloud · DEM · road settlement · deformation extraction · change detection · InSAR/PS-InSAR/MT-InSAR · Sentinel-1 · slope aspect · subsidence
- **C 冻土工程风险与机器学习**：permafrost · risk assessment · machine learning · susceptibility mapping · numerical simulation · deformation prediction · deep learning · climate projection

## 中文库（知网/万方）

`cnki_query.py` 读 `cnki_query`/`wanfang_query` 字段直接输出，用户复制去平台**手动**检索（无合法自动接口）。知网专业检索语法：`SU=`主题、`TI=`题名、`KY=`关键词、`AB=`摘要；`*`模糊、`=`精确；`AND/OR/NOT` 组合。
