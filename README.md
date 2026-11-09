# ICDSearcher 部署指引

独立检索 Asser Institute 的 International Crimes Database（ICD）。只访问 `internationalcrimesdatabase.org`。

仓库：<https://github.com/HuiwowICCSkills/ICDSearcher>（私有）。

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
