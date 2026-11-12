#!/usr/bin/env python3
"""International Crimes Database adapter for ICDSearcher."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from skillkit import HTTP, RetrievalError, clean, result, terms

PROG = "icd_search.py"
DESCRIPTION = "Search the Asser Institute International Crimes Database."
CACHE_DEFAULT = ".icd-cache"
FETCH_TIMEOUT_DEFAULT = 300

SEARCH_URL = "https://www.internationalcrimesdatabase.org/SearchResults/"
PAGE_SIZE = 5
FALLBACK_PAGES = 6
CATEGORIES = {
    "genocide": "1",
    "war crimes": "2",
    "crimes against humanity": "3",
    "crime of aggression": "4",
    "aggression": "4",
    "torture": "5",
    "piracy": "6",
    "terrorism": "10",
}
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/155.0.0.0 Safari/537.36"
)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def make_http(args: argparse.Namespace) -> HTTP:
    return HTTP(
        args.cache,
        offline=args.offline,
        ttl=args.cache_ttl,
        timeout=args.timeout,
        user_agent=UA,
    )


def add_search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=10, help="1..50 (default 10)")
    parser.add_argument("--offset", type=int, default=0, help=">= 0 (default 0)")
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help=(
            "ICD crime category, repeatable: genocide, 'war crimes', "
            "'crimes against humanity', aggression, torture, piracy, terrorism, "
            "or the numeric id 1/2/3/4/5/6/10"
        ),
    )
    parser.add_argument("--year-from", dest="year_from", help="Earliest case year (advanced search)")
    parser.add_argument("--year-to", dest="year_to", help="Latest case year (advanced search)")
    parser.add_argument(
        "--no-term-fallback",
        action="store_true",
        help="Do not retry a blocked phrase as a term-by-term intersection",
    )


def add_fetch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text-out", help="Write extracted page text here")


def _category_ids(values: list[str]) -> list[str]:
    ids: list[str] = []
    for value in values:
        key = str(value).strip().casefold()
        if key.isdigit():
            ids.append(key)
        elif key in CATEGORIES:
            ids.append(CATEGORIES[key])
        else:
            raise ValueError(
                "Unknown ICD category "
                + repr(value)
                + "; use one of "
                + ", ".join(sorted(CATEGORIES))
            )
    return list(dict.fromkeys(ids))


def _filters(args: argparse.Namespace) -> dict[str, str]:
    result: dict[str, str] = {}
    categories = _category_ids(getattr(args, "category", []) or [])
    if categories:
        result["cat"] = ",".join(categories)
        result["a"] = "1"
    if getattr(args, "year_from", None):
        result["fy"] = str(args.year_from)
        result["a"] = "1"
    if getattr(args, "year_to", None):
        result["ty"] = str(args.year_to)
        result["a"] = "1"
    return result


def _results_page(
    http: HTTP, query: str, page: int, filters: dict[str, str] | None = None
) -> tuple[list[dict[str, Any]], int, int]:
    params = {"q": query, "p": str(page), **(filters or {})}
    soup, meta = http.soup(SEARCH_URL, params, headers=_headers())
    block = soup.select_one("div.search-results")
    if block is None:
        raise RetrievalError(
            "ICD search results container missing; page layout changed or request filtered"
        )
    head = block.find("h2")
    label = clean(head.get_text(" ", strip=True)) if head else ""
    if re.search(r"no results", label, re.I):
        return [], 0, 0
    count = re.search(r"(\d+)\s+results", label)
    if not count:
        raise RetrievalError("ICD result count not recognised: " + label[:80])
    total = int(count.group(1))
    paging = re.search(r"page\s+(\d+)\s+of\s+(\d+)", block.get_text(" ", strip=True), re.I)
    pages = int(paging.group(2)) if paging else page
    nodes = [node for node in block.children if getattr(node, "name", None)]
    rows: list[dict[str, Any]] = []
    for index, node in enumerate(nodes):
        if node.name != "strong":
            continue
        link = node.find("a", href=re.compile(r"/Case/\d+"))
        if not link:
            continue
        name = link.find("strong")
        title = clean(link.get_text(" ", strip=True))
        case_name = clean(name.get_text(" ", strip=True)) if name else title
        subtitle = title[len(case_name) :].lstrip(" :") if name else ""
        citation = summary = ""
        for following in nodes[index + 1 :]:
            if following.name == "strong":
                break
            if not citation and following.name == "p":
                citation = clean(following.get_text(" ", strip=True))
            elif not summary and following.name == "div" and "search-summary" in (following.get("class") or []):
                summary = clean(following.get_text(" ", strip=True))
        date = re.search(r"\b\d{1,2}\s+[A-Z][a-z]{2,8}\s+\d{4}\b", citation)
        rows.append(
            result(
                title,
                urljoin(meta["source_url"], link["href"]),
                "icd-search",
                summary or citation,
                case_name=case_name,
                subtitle=subtitle,
                citation=citation,
                date=date.group(0) if date else None,
                access="public ICD search-result page: case name, citation and summary snippet",
                content_scope="ICD search result; the detail page and any linked judgment must be fetched separately",
            )
        )
    return rows, total, pages


def _search_phrase(
    http: HTTP,
    query: str,
    limit: int,
    offset: int,
    filters: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = (offset // PAGE_SIZE) * PAGE_SIZE
    page = base // PAGE_SIZE + 1
    end = offset + limit
    rows: list[dict[str, Any]] = []
    total = pages = None
    fetched = 0
    while (page - 1) * PAGE_SIZE < end and fetched < 20:
        batch, total, pages = _results_page(http, query, page, filters)
        rows.extend(batch)
        fetched += 1
        if not batch or (pages and page >= pages):
            break
        page += 1
    selected = rows[offset - base : offset - base + limit]
    more = total is None or offset + len(selected) < total
    return selected, {
        "total": total,
        "offset": offset,
        "limit": limit,
        "page_size": PAGE_SIZE,
        "page": base // PAGE_SIZE + 1,
        "pages": pages,
        "pages_fetched": fetched,
        "next_offset": offset + len(selected) if selected and more else None,
    }


def _token_fallback(
    http: HTTP,
    query: str,
    limit: int,
    offset: int,
    filters: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tokens = list(dict.fromkeys(terms(query)))[:4]
    if len(tokens) < 2:
        raise RetrievalError("ICD phrase rejected but no multi-term fallback applies: " + query)
    per_token: list[tuple[str, dict[str, dict[str, Any]]]] = []
    for token in tokens:
        seen: dict[str, dict[str, Any]] = {}
        for page in range(1, FALLBACK_PAGES + 1):
            batch, total, pages = _results_page(http, token, page, filters)
            if not batch:
                break
            for row in batch:
                seen.setdefault(row["url"], row)
            if pages and page >= pages:
                break
        per_token.append((token, seen))
    common = set.intersection(*[set(seen) for _, seen in per_token])
    ordered = [row for url, row in per_token[0][1].items() if url in common]
    for row in ordered:
        row["via"] = "icd-token-intersection"
        row["matched_terms"] = tokens
        row["access"] = (
            "public ICD search results matched term-by-term and intersected locally; "
            f"bounded to {FALLBACK_PAGES} result pages per term, not the site ranking"
        )
    info = {
        "terms": tokens,
        "pages_per_term": FALLBACK_PAGES,
        "candidates_per_term": {token: len(seen) for token, seen in per_token},
        "total": len(ordered),
        "offset": offset,
        "limit": limit,
        "next_offset": offset + limit if offset + limit < len(ordered) else None,
    }
    return ordered[offset : offset + limit], info


def search(query: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("A non-empty query is required")
    if not 1 <= args.limit <= 50:
        raise ValueError("limit must be 1..50")
    if args.offset < 0:
        raise ValueError("offset must be >= 0")
    warnings: list[str] = []
    filters = _filters(args)
    try:
        rows, pagination = _search_phrase(http, query, args.limit, args.offset, filters)
        via = "icd-search"
    except RetrievalError as exc:
        if args.no_term_fallback:
            raise
        warnings.append("ICD phrase search failed; using bounded term intersection: " + str(exc))
        rows, pagination = _token_fallback(http, query, args.limit, args.offset, filters)
        via = "icd-token-intersection"
    total = pagination.get("total")
    return {
        "status": "ok" if rows or total == 0 else "no-results-in-queried-index",
        "query": query,
        "filters": filters,
        "total": total,
        "results": rows,
        "pagination": pagination,
        "warnings": warnings,
        "scope": (
            "International Crimes Database (Asser Institute) public case search; "
            "five rows per page and relevance-ranked; category and year filters use "
            "the site's AdvancedSearch parameters"
        ),
        "evidence": http.evidence,
    }


def fetch(locator: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    parsed = urlparse(locator)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "www.internationalcrimesdatabase.org":
        raise ValueError("fetch expects an https://www.internationalcrimesdatabase.org/ URL")
    soup, meta = http.soup(locator, headers=_headers())
    container = (
        soup.select_one("main")
        or soup.select_one("#main")
        or soup.select_one(".container")
        or soup.body
        or soup
    )
    for node in container.select("script, style, nav, header, footer, input, select, button, textarea, noscript"):
        node.decompose()
    text = container.get_text("\n", strip=True)
    if len(text) < 100:
        raise RetrievalError("Insufficient ICD page text; page may be a shell or access page")
    links = []
    seen = set()
    for anchor in container.select("a[href]"):
        href = urljoin(meta["source_url"], anchor["href"])
        if href in seen:
            continue
        seen.add(href)
        links.append({"text": clean(anchor.get_text(" ", strip=True)), "url": href})
    if args.text_out:
        Path(args.text_out).write_text(text, encoding="utf-8")
    return {
        "status": "ok",
        "url": meta["source_url"],
        "title": clean(soup.title.get_text(" ", strip=True)) if soup.title else "",
        "text": text,
        "text_characters": len(text),
        "document_links": links,
        "content_scope": "ICD case detail page text; linked judgments must be fetched separately",
        "text_out": str(Path(args.text_out).resolve()) if args.text_out else None,
        "sha256": meta["sha256"],
        "retrieved_at": meta["retrieved_at"],
    }


def doctor(args: argparse.Namespace) -> dict[str, Any]:
    checks = [
        {"check": "python", "ok": True, "detail": "Python runtime available"},
        {"check": "requests", "ok": True, "detail": "requests importable"},
        {"check": "beautifulsoup4", "ok": True, "detail": "bs4 importable"},
    ]
    if args.no_probe:
        return {"ok": True, "status": "ok (probes skipped)", "checks": checks}
    http = make_http(args)
    try:
        rows, total, pages = _results_page(http, "genocide", 1)
        checks.append(
            {
                "check": "ICD search",
                "ok": bool(rows),
                "total": total,
                "pages": pages,
            }
        )
        ok = bool(rows)
    except Exception as exc:
        checks.append({"check": "ICD search", "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        ok = False
    return {"ok": ok, "status": "ok" if ok else "error", "checks": checks, "catalog": {"search_url": SEARCH_URL}}
