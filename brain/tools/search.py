# ============================================================
# LavOS 2026 — brain/tools/search.py  (finds things online)
# Web search via DuckDuckGo (no API key needed).
# Returns top snippets + source links.
# ============================================================

import urllib.request
import urllib.parse
import re


def web_search(query: str = "", max_results: int = 3, **_) -> dict:
    """Search the web via DuckDuckGo HTML (no API key). Returns top snippets."""
    if not query.strip():
        return {"ok": False, "result": "Empty search query", "data": {}}

    # Strip trailing punctuation that breaks search
    clean_query = re.sub(r'[!?.,;:]+$', '', query).strip()
    if not clean_query:
        clean_query = query

    try:
        url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": clean_query})
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LavOS/2026"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="replace")

        # Parse results from HTML
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        urls = re.findall(
            r'class="result__url"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        # Deduplicate by URL
        seen_urls = set()
        results = []
        for i in range(min(max_results * 2, len(snippets))):
            if len(results) >= max_results:
                break
            title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
            url_text = re.sub(r'<[^>]+>', '', urls[i]).strip() if i < len(urls) else ""
            if url_text in seen_urls:
                continue
            seen_urls.add(url_text)
            results.append({
                "title": title,
                "snippet": snippet,
                "url": url_text,
            })

        if not results:
            return {"ok": True, "result": f"No results for: {clean_query}", "data": {"results": []}}

        text = "\n".join(
            f"{i+1}. {r['title']}\n   {r['snippet']}"
            for i, r in enumerate(results)
        )
        return {"ok": True, "result": text, "data": {"results": results}}

    except Exception as e:
        return {"ok": False, "result": f"Search failed (offline?): {e}", "data": {}}
