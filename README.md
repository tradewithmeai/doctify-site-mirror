# Doctify.com Site Mirror 💪💉  
*A structured web scraping and mirroring system built for analysis and schema design.*

---

## 🔍 Overview
This project mirrors selected sections of [Doctify.com](https://www.doctify.com) into **local storage** for offline, structured analysis.  
It’s designed to demonstrate safe, ethical web scraping practices using:

- **Requests + BeautifulSoup** for static content  
- **Playwright** for dynamic (JavaScript-rendered) content  
- **Modular architecture** for incremental crawling, rendering, and schema generation  

All scraped content stays local — no external distribution or automated uploads.

---

## 🧱 Project Structure
```
site-mirror/
├─ crawl_static.py         # Static page crawler (Requests + BeautifulSoup)
├─ render_dynamic.py       # Dynamic renderer (Playwright)
├─ setup.bat               # Windows setup script (creates venv, installs deps, runs crawler)
├─ mirror/
│   ├─ raw/                # Raw static HTML
│   ├─ rendered/           # Rendered (JS-loaded) HTML
│   ├─ meta/               # Logs, URL index, crawl metadata
│   ├─ extracted/          # Basic triage data (titles, links, h1s)
└─ README.md
```

---

## ⚙️ Setup Instructions

### 🪟 For Windows
1. **Double-click** `setup.bat`  
   - Creates virtual environment  
   - Installs all dependencies  
   - Starts the static crawl  
   - Optionally launches Playwright renderer  

2. Wait for completion — the crawler runs politely (1 req/sec) and auto-stops after 500 pages.  

3. When prompted, choose whether to run the **dynamic renderer** immediately.

---

## 🧠 How It Works
1. **Static Phase** (`crawl_static.py`)
   - Loads sitemap and robots.txt  
   - Crawls up to 500 unique internal pages  
   - Saves HTML to `mirror/raw`  
   - Generates triage records (`mirror/extracted/quick_index.jsonl`)  
   - Detects JavaScript-heavy pages and queues them for dynamic rendering  

2. **Dynamic Phase** (`render_dynamic.py`)
   - Reads `mirror/meta/dynamic_queue.txt`  
   - Uses Playwright to render full DOM  
   - Saves rendered HTML to `mirror/rendered`  
   - Appends metadata to `crawl_index.jsonl`  

3. **Analysis Phase** (Planned)
   - A Claude Code agent will scan the mirrored HTML  
   - Generate an entity-relationship schema for structured scraping  
   - Produce extraction selectors and data validation pipelines  

---

## 📦 Dependencies
- Python ≥ 3.10  
- `requests`, `beautifulsoup4`, `playwright`  

(Installed automatically by `setup.bat`)

---

## 🧩 Output Files

| File | Purpose |
|------|----------|
| `mirror/meta/crawl_index.jsonl` | Log of all crawled pages |
| `mirror/meta/dynamic_queue.txt` | URLs requiring Playwright rendering |
| `mirror/meta/seen_urls.txt` | Resume checkpoint (avoids duplicate crawling) |
| `mirror/extracted/quick_index.jsonl` | Lightweight index for schema planning |

---

## 🔬 Future Expansion
- **Claude Code integration** to auto-generate scraping schemas.  
- **Entity validation pipeline** using Pydantic or Schematics.  
- **Delta monitoring** (detect changed pages by hash).  
- **Configurable concurrency and rate limits.**

---

## ⚠️ Ethical and Legal Notes
This project follows ethical scraping principles:
- Respects `robots.txt`  
- Throttles requests  
- Stores content locally only  
- No data redistribution  

Use strictly for **research and demonstration**.

---

## 🧠 Author
**Captain (SolVX)**  
Exploring AI(L) applications for structured data analysis and automation.  
💼 [solvx.uk](https://solvx.uk)

