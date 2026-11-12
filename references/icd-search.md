# ICD 检索实测记录（2026-11-09）

## 端点

`https://www.internationalcrimesdatabase.org/SearchResults/?q=<query>&p=<page>`

- 每页固定 5 条
- 结果容器：`div.search-results`
- 标题：`h2` 中的 `N results (ordered by relevance)`
- 行：`strong` 内的 `a[href*="/Case/"]`
- citation：后续 `p`
- 摘要：`div.search-summary`

实测 `genocide --limit 3` → `status=ok`、`total=224`、3 条；第一条 `Bugingo : Public Prosecutor v. Sadi Bugingo`，`/Case/919`。

## 短语 403

`command responsibility` 这类 `command + 空格 + 词` 的短语会被 Azure 前端拦截（403）。适配器改为逐词检索并取交集，标为 `icd-token-intersection`，最多每词 6 页；`--no-term-fallback` 可关闭。

## 详情页

`https://www.internationalcrimesdatabase.org/Case/919` → `status=ok`、`text_characters=2686`；详情页可能只是案件介绍，判决 PDF 在链接的另一端。

## 边界

`total` 来自结果页标题，不是已抓取数；ICD 摘要不是判决理由。

## Advanced Case Search（2026-11-12 浏览器核对）

页面：`https://www.internationalcrimesdatabase.org/AdvancedSearch`。提交后落在
`https://www.internationalcrimesdatabase.org/SearchResults/?q=<词>&cat=<id,...>&fy=<年>&ty=<年>&a=1`。

| 参数 | 含义 | 值 |
| --- | --- | --- |
| `q` | 检索词 | 任意关键词 |
| `cat` | 罪名类别，逗号分隔 | `1` genocide，`2` war crimes，`3` crimes against humanity，`4` crime of aggression，`5` torture，`6` piracy，`10` terrorism |
| `fy` / `ty` | 年份起止 | 四位年份 |
| `a` | 高级检索标记 | `1` |

实测 `q=genocide` → 224 条；`q=genocide&cat=1,3&fy=2000&ty=2020` → 171 条。高级表单本身对 `command responsibility` 仍会被 Azure Application Gateway 以 403 拦截，浏览器和 `requests` 都一样；这是站点前门策略，不是零结果。
