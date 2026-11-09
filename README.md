# ICDSearcher 部署指引

独立检索 Asser Institute 的 International Crimes Database（ICD）。只访问 `internationalcrimesdatabase.org`。

仓库：<https://github.com/HuiwowICCSkills/ICDSearcher>（公开）。

## 1. 环境

Python 3.10+，依赖 `requests`、`beautifulsoup4`、`pypdf`；无需浏览器或登录。

## 2. 安装

```powershell
git clone https://github.com/HuiwowICCSkills/ICDSearcher.git "$env:USERPROFILE\.codex\skills\ICDSearcher"
python -m pip install -r "$env:USERPROFILE\.codex\skills\ICDSearcher\requirements.txt"
```

## 3. 自检

```powershell
& "$env:USERPROFILE\.codex\skills\ICDSearcher\run.ps1" doctor
```

## 4. 使用

```powershell
$icd = "$env:USERPROFILE\.codex\skills\ICDSearcher\run.ps1"
& $icd search 'genocide' --limit 10 --out './icd.json'
& $icd fetch 'https://www.internationalcrimesdatabase.org/Case/919' --out './case.json' --text-out './case.txt'
```

## 5. 排错

| 现象 | 处理 |
| --- | --- |
| 短语 403 | 适配器自动逐词交集；结果 `via=icd-token-intersection`，不是站点短语检索 |
| 页面布局变化 | `search-results` 容器或结果计数缺失时会报错，不会静默返回空结果 |
| 每页只有 5 条 | 站点固定分页；用 `pagination.next_offset` 或 `--offset` 续页 |

## 6. 边界

ICD 是案件数据库，详情页可能只是案件介绍；判决全文在链接的另一端。引用前读取原始判决，不要把 ICD 摘要当裁判理由。

## 实测效果（2026-11-09）

以下命令与结果来自本机 `~/.codex/skills/ICDSearcher` 的实网运行；检索日期 2026-11-09（Asia/Shanghai），输出为该次运行实际返回的 JSON 报告。

```powershell
& .\run.ps1 search 'genocide' --limit 5
```

- 状态：`ok`；服务端/索引报告 `total = 224`；本次返回 5 条。
- 代表性结果：

| 题名 | 类型 / 日期 | 链接 |
| --- | --- | --- |
| Bugingo : Public Prosecutor v. Sadi Bugingo | retrieved_metadata；14 Feb 2013 | https://www.internationalcrimesdatabase.org/Case/919 |
| Basebya : The Prosecutor v. Yvonne Basebya | retrieved_metadata；1 Mar 2013 | https://www.internationalcrimesdatabase.org/Case/971 |
| Ríos Montt : Rigoberta Menchu et al. v Ríos Montt et al. | retrieved_metadata；20 May 2013 | https://www.internationalcrimesdatabase.org/Case/948 |

> 说明：`total = 224` 是 ICD 站点对 `genocide` 的命中数（`scope`：Asser Institute 的 International Crimes Database 公开案件检索，站点固定每页 5 条、按相关度排序，`pagination.pages = 45`），不是判决数量。返回结果均为案件元数据与摘要片段（`result_type = retrieved_metadata`），`content_scope` 明确写明"ICD search result; the detail page and any linked judgment must be fetched separately"。因此本段只能证明检索通道可用、命中与元数据正确；判决全文须用 `fetch` 另行读取原文，引用前不得把 ICD 摘要当作裁判理由。