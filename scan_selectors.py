#!/usr/bin/env python3
"""
Scan mirror HTML files to identify real selectors for schema extraction.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup

def scan_html_files(mirror_dir, max_files=60):
    """Scan HTML files and identify selectors"""

    results = defaultdict(lambda: {"pages": [], "selector_hits": defaultdict(int)})
    rendered_dir = Path(mirror_dir) / "rendered"

    html_files = list(rendered_dir.rglob("*.html"))
    print(f"Found {len(html_files)} HTML files, scanning up to {max_files}...")

    # Categorize files by URL pattern
    blog_posts = []
    case_studies = []
    other_pages = []

    for html_file in html_files:
        path_str = str(html_file).replace("\\", "/")  # Normalize path separators
        if "/blog/posts/" in path_str and "/page/" not in path_str and "/categories/" not in path_str:
            blog_posts.append(html_file)
        elif "/case-studies/" in path_str or "/case-study/" in path_str:
            case_studies.append(html_file)
        else:
            other_pages.append(html_file)

    print(f"\nCategorized files:")
    print(f"  Blog posts: {len(blog_posts)}")
    print(f"  Case studies: {len(case_studies)}")
    print(f"  Other pages: {len(other_pages)}")

    # Sample files from each category
    sample_blog = blog_posts[:30]
    sample_case = case_studies[:10]
    sample_other = other_pages[:20]

    samples = sample_blog + sample_case + sample_other

    print(f"\nScanning {len(samples)} sample files...\n")

    for i, html_file in enumerate(samples):
        if i >= max_files:
            break

        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')

                page_type = "unknown"
                if html_file in blog_posts:
                    page_type = "blog_post"
                elif html_file in case_studies:
                    page_type = "case_study"

                # Extract metadata and selectors
                analyze_page(soup, page_type, results, str(html_file.relative_to(rendered_dir)))

                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(samples)} files...")

        except Exception as e:
            print(f"Error processing {html_file}: {e}")

    return results

def analyze_page(soup, page_type, results, file_path):
    """Analyze a single page and record selectors"""

    data = {"file": file_path, "selectors": {}}

    # Title selectors
    title_selectors = [
        ('title', lambda s: s.find('title')),
        ('meta[og:title]', lambda s: s.find('meta', property='og:title')),
        ('h1', lambda s: s.find('h1')),
        ('h1.elementor-heading-title', lambda s: s.find('h1', class_='elementor-heading-title')),
        ('.elementor-widget-theme-post-title h1', lambda s: s.select_one('.elementor-widget-theme-post-title h1')),
    ]

    for selector_name, selector_func in title_selectors:
        elem = selector_func(soup)
        if elem:
            text = elem.get('content') if elem.name == 'meta' else elem.get_text(strip=True)
            if text:
                data["selectors"]["title"] = data["selectors"].get("title", [])
                data["selectors"]["title"].append({
                    "selector": selector_name,
                    "sample": text[:100]
                })

    # Canonical URL
    canonical_selectors = [
        ('link[rel="canonical"]', lambda s: s.find('link', rel='canonical')),
        ('meta[property="og:url"]', lambda s: s.find('meta', property='og:url')),
    ]

    for selector_name, selector_func in canonical_selectors:
        elem = selector_func(soup)
        if elem:
            url = elem.get('href') or elem.get('content')
            if url:
                data["selectors"]["canonical_url"] = data["selectors"].get("canonical_url", [])
                data["selectors"]["canonical_url"].append({
                    "selector": selector_name,
                    "sample": url[:100]
                })

    # Author
    author_selectors = [
        ('meta[name="author"]', lambda s: s.find('meta', attrs={'name': 'author'})),
        ('.elementor-post-info__item--type-author', lambda s: s.select_one('.elementor-post-info__item--type-author')),
        ('[itemprop="author"]', lambda s: s.find(attrs={'itemprop': 'author'})),
    ]

    for selector_name, selector_func in author_selectors:
        elem = selector_func(soup)
        if elem:
            text = elem.get('content') if elem.name == 'meta' else elem.get_text(strip=True)
            if text:
                data["selectors"]["author"] = data["selectors"].get("author", [])
                data["selectors"]["author"].append({
                    "selector": selector_name,
                    "sample": text[:100]
                })

    # Published date
    date_selectors = [
        ('meta[property="article:published_time"]', lambda s: s.find('meta', property='article:published_time')),
        ('time[datetime]', lambda s: s.find('time', attrs={'datetime': True})),
        ('.elementor-post-info__item--type-date', lambda s: s.select_one('.elementor-post-info__item--type-date')),
    ]

    for selector_name, selector_func in date_selectors:
        elem = selector_func(soup)
        if elem:
            date = elem.get('content') or elem.get('datetime') or elem.get_text(strip=True)
            if date:
                data["selectors"]["published_date"] = data["selectors"].get("published_date", [])
                data["selectors"]["published_date"].append({
                    "selector": selector_name,
                    "sample": date[:50]
                })

    # Content
    content_selectors = [
        ('.elementor-widget-theme-post-content', lambda s: s.select_one('.elementor-widget-theme-post-content')),
        ('.post-content-container', lambda s: s.select_one('.post-content-container')),
        ('article .entry-content', lambda s: s.select_one('article .entry-content')),
        ('.blog-content', lambda s: s.select_one('.blog-content')),
        ('main article', lambda s: s.select_one('main article')),
    ]

    for selector_name, selector_func in content_selectors:
        elem = selector_func(soup)
        if elem:
            text = elem.get_text(strip=True)
            if text and len(text) > 100:  # Only count substantial content
                data["selectors"]["content"] = data["selectors"].get("content", [])
                data["selectors"]["content"].append({
                    "selector": selector_name,
                    "sample": text[:200]
                })

    # JSON-LD structured data
    json_ld = soup.find('script', type='application/ld+json')
    if json_ld:
        try:
            ld_data = json.loads(json_ld.string)
            data["selectors"]["json_ld"] = [{
                "selector": "script[type='application/ld+json']",
                "sample": "Found"
            }]
        except:
            pass

    # Record results
    if data["selectors"]:
        results[page_type]["pages"].append(data)

    # Count selector hits
    for field, selectors in data["selectors"].items():
        for sel_info in selectors:
            selector = sel_info["selector"]
            results[page_type]["selector_hits"][f"{field}::{selector}"] += 1

if __name__ == "__main__":
    mirror_dir = "mirror"

    results = scan_html_files(mirror_dir, max_files=60)

    print("\n" + "="*80)
    print("SELECTOR ANALYSIS RESULTS")
    print("="*80)

    for page_type in results:
        if page_type == "pages":
            continue
        print(f"\n{page_type.upper()}:")
        print(f"  Pages analyzed: {len(results[page_type]['pages'])}")
        print(f"\n  Selector hit rates:")

        hits = dict(results[page_type]["selector_hits"])
        for field_selector, count in sorted(hits.items(), key=lambda x: (-x[1], x[0])):
            field = field_selector.split("::")[0]
            selector = field_selector.split("::")[1]
            print(f"    {field:20s} | {selector:50s} | {count:3d} hits")

    # Save results
    output_file = "mirror/extracted/selector_scan_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Convert defaultdict to regular dict for JSON serialization
    output_data = {}
    for page_type in results:
        output_data[page_type] = {
            "pages": results[page_type]["pages"],
            "selector_hits": dict(results[page_type]["selector_hits"])
        }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n\nDetailed results saved to: {output_file}")
