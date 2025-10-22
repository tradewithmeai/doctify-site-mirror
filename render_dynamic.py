import asyncio, json, hashlib
from pathlib import Path
from playwright.async_api import async_playwright
import urllib.parse as up

OUT = Path("mirror")
REND = OUT / "rendered"
META = OUT / "meta"
REND.mkdir(parents=True, exist_ok=True)

def url_to_path(u: str) -> Path:
    sp = up.urlsplit(u)
    path = sp.path.rstrip("/")
    if not path:
        path = "/"
    safe = (sp.netloc + path).rstrip("/")
    if path.endswith((".html", ".htm")):
        p = REND / safe
    else:
        p = REND / safe / "index.html"
    return p

async def render(urls):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent="SolVX-Mirror/1.0 (Playwright)")
        page = await ctx.new_page()
        idx_fp = (META / "crawl_index.jsonl").open("a", encoding="utf-8")

        for url in urls:
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                # Gentle scroll to load lazy elements
                for _ in range(5):
                    await page.mouse.wheel(0, 1200)
                    await page.wait_for_timeout(400)

                html = await page.content()
                path = url_to_path(url)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(html, encoding="utf-8")

                h = hashlib.sha256(html.encode("utf-8")).hexdigest()
                idx_fp.write(json.dumps({
                    "url": url,
                    "status": 200,
                    "sha256": h,
                    "saved": str(path.relative_to(OUT)),
                    "type": "rendered",
                }) + "\n")
                idx_fp.flush()
                await page.wait_for_timeout(500)

            except Exception as e:
                print(f"[WARN] Failed {url}: {e}")
                continue

        await browser.close()

def unique_urls():
    q = META / "dynamic_queue.txt"
    if not q.exists():
        return []
    seen, urls = set(), []
    for line in q.read_text(encoding="utf-8").splitlines():
        u = line.strip()
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    return urls

if __name__ == "__main__":
    urls = unique_urls()
    if urls:
        asyncio.run(render(urls))
    else:
        print("No dynamic URLs found.")
