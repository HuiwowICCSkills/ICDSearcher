---
name: ICDSearcher
description: 独立检索 Asser Institute 的 International Crimes Database（ICD），按关键词查找国际犯罪案件、citation 和摘要；支持短语被 WAF 拦截时的有界词项交集回退，并可读取案件详情页。
---

# ICDSearcher

> **`<skill-dir>`** = 本 SKILL.md 所在目录。核心脚本为 `<skill-dir>/scripts/icd_search.py`；Windows 用 `<skill-dir>/run.ps1`，macOS/Linux 用 `<skill-dir>/run.sh`。部署与排错见 [README.md](README.md)。

这个 skill 只做 `internationalcrimesdatabase.org` 一个站点：

- `search`：公开 `SearchResults` 页面，每页固定 5 条；返回案名、citation、摘要片段和详情页链接；
- `fetch`：读取 `/Case/<id>` 详情页，返回正文和文书链接；
- `doctor`：检查依赖并探测 ICD 搜索页。

## 命令

```powershell
& '<skill-dir>/run.ps1' search 'genocide' --limit 10 --out './icd-search.json'
& '<skill-dir>/run.ps1' search 'command responsibility' --limit 5 --no-term-fallback
& '<skill-dir>/run.ps1' fetch 'https://www.internationalcrimesdatabase.org/Case/919' --out './icd-case.json' --text-out './icd-case.txt'
& '<skill-dir>/run.ps1' doctor
```

通用参数：`--out`、`--cache`、`--cache-ttl`、`--offline`、`--timeout`。`search` 另有 `--limit`（1..50）、`--offset`、`--no-term-fallback`；`fetch` 另有 `--text-out`。

## 结果边界

- ICD 搜索结果是**案件检索页**：案名、citation 和摘要片段，不是判决全文；详情页也可能只是案件介绍，真正的判决 PDF 在链接的另一端。
- ICD 的 ASP.NET 前端对某些含 `command + 空格 + 词` 的短语会返回 Azure 前端 403。适配器会改为逐词检索并取交集，结果标为 `icd-token-intersection`，这是**有界近似**，不是站点自身的短语排序；`--no-term-fallback` 可关闭。
- 每页固定 5 条，适配器最多抓取 20 页；`total` 来自页面标题的 “N results”，不是已抓取条数。
- `status=error` 或 403 只是本次请求受限，不等于 ICD 没有相关资料。

## 参考

- 2026-11-09 实测：搜索页选择器、`genocide` 的 224 条结果、`command responsibility` 的 403 与词项回退：[references/icd-search.md](references/icd-search.md)
- 部署、环境与排错：[README.md](README.md)
