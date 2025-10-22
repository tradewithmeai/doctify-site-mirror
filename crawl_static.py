import time, os, hashlib, json, re, urllib.parse as up
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib import robotparser
from collections import deque

ROOT = "https://www.doctify.com"
OUT = Path("mirror")
RAW = OUT / "raw"
META = OUT / "meta"
EXTRACTED = OUT / "extracted"
RAW.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)
EXTRACTED.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "SolVX-Mirror/1.0 (+contact: you@example.com)"
})

def canon(u: str) -> str:
    u = up.urlsplit(up.urljoin(ROOT, u))
    q = up.parse_qsl(u.query, keep_blank_values=False)
    q = [(k, v) for (k, v) in q if k.lower() not in {"utm_source","utm_medium","utm_campaign","gclid"}]
    u = u._replace(query=up.urlencode(sorted(q)))
    return up.urlunsplit(u)

def in_scope(u: str) -> bool:
    return up.urlsplit(u).netloc.endswith(up.urlsplit(ROOT).netloc)

def url_to_path(u: str) -> Path:
    sp = up.urlsplit(u)
    path = sp.path.rstrip("/")
    if not path:
        path = "/"
    safe = (sp.netloc + path).rstrip("/")
    if path.endswith((".html", ".htm")):
        p = RAW / safe
    else:
        p = RAW / safe / "index.html"
    return p

def save_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def load_robots(root: str):
    rp = robotparser.RobotFileParser()
    rp.set_url(up.urljoin(root, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass
    return rp

def sitemap_seeds(root: str):
    seeds = set()
    try:
        r = SESSION.get(up.urljoin(root, "/sitemap.xml"), timeout=20)
        if r.ok:
            soup = BeautifulSoup(r.text, "xml")
            for loc in soup.find_all("loc"):
                seeds.add(canon(loc.text.strip()))
    except Exception:
        pass
    return seeds

def likely_dynamic(html: str) -> bool:
    if "enable javascript" in html.lower():
        return True
    scripts = html.lower().count("<script")
    txt = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return scripts > 20 or len(txt) < 400

def triage_record(url: str, html: str):
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    h1 = (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
    links = sorted({canon(a.get("href","")) for a in soup.find_all("a", href=True) if in_scope(a["href"])})
    return {"url": url, "title": title, "h1": h1, "links": links[:200]}

def load_seen():
    seen_file = META / "seen_urls.txt"
    if seen_file.exists():
        return set(seen_file.read_text(encoding="utf-8").splitlines())
    return set()

def save_seen(seen):
    seen_file = META / "seen_urls.txt"
    seen_file.write_text("\n".join(sorted(seen)), encoding="utf-8")

def main():
    rp = load_robots(ROOT)
    seeds = sitemap_seeds(ROOT) or {ROOT}
    # Expand seeds for Stage 4: practitioners, clinics, specialists
    seeds |= {
        canon("https://www.doctify.com/uk/doctor/"),
        canon("https://www.doctify.com/uk/clinic/"),
        canon("https://www.doctify.com/uk/specialists/"),
    }
    q = deque(sorted(seeds))
    seen = load_seen()
    crawl_delay = 1.0
    max_pages = 1200  # increased for Stage 4 expansion
    processed = 0

    idx_fp = (META / "crawl_index.jsonl").open("a", encoding="utf-8")
    triage_fp = (EXTRACTED / "quick_index.jsonl").open("a", encoding="utf-8")
    dyn_fp = (META / "dynamic_queue.txt").open("a", encoding="utf-8")

    while q and processed < max_pages:
        url = q.popleft()
        if url in seen:
            continue
        seen.add(url)
        processed += 1
        try:
            if rp and not rp.can_fetch(SESSION.headers["User-Agent"], url):
                continue
            r = SESSION.get(url, timeout=25)
            time.sleep(crawl_delay)
        except Exception as e:
            print(f"[WARN] Skipped {url}: {e}")
            continue
        if not r.ok:
            continue

        html = r.text
        path = url_to_path(url)
        save_text(path, html)
        h = hashlib.sha256(html.encode("utf-8")).hexdigest()

        rec = triage_record(url, html)
        for link in rec["links"]:
            if in_scope(link) and link not in seen:
                q.append(link)

        if likely_dynamic(html):
            dyn_fp.write(url + "\n")
            dyn_fp.flush()

        idx_fp.write(json.dumps({
            "url": url,
            "status": r.status_code,
            "sha256": h,
            "saved": str(path.relative_to(OUT)),
            "type": "static",
        }) + "\n")
        idx_fp.flush()

        triage_fp.write(json.dumps(rec) + "\n")
        triage_fp.flush()

        if processed % 50 == 0:
            save_seen(seen)
            print(f"[INFO] Processed {processed} pages...")

    save_seen(seen)
    print(f"\n[INFO] Crawl complete — processed {processed} pages.\n")

if __name__ == "__main__":
    main()
