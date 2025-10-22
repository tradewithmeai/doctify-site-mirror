#!/usr/bin/env python3
"""
Doctify Site Mirror Extraction Pipeline
Extracts structured data from HTML files using BeautifulSoup based on schema definitions.
"""

import json
import re
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
import hashlib
import unicodedata
import logging

try:
    from bs4 import BeautifulSoup
    import yaml
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install beautifulsoup4 pyyaml lxml")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DoctifyExtractor:
    """Main extractor class for Doctify site mirror data"""

    def __init__(self, schema_dir: str = "schema", mirror_dir: str = "mirror"):
        """
        Initialize the extractor with schema and mirror directories.

        Args:
            schema_dir: Path to directory containing schema YAML files
            mirror_dir: Path to mirror directory containing HTML files
        """
        self.schema_dir = Path(schema_dir)
        self.mirror_dir = Path(mirror_dir)
        self.entities_schema = None
        self.selectors_schema = None

        # Track selector hit rates
        self.selector_hits = {}

        # Load schemas
        self._load_schemas()

    def _load_schemas(self):
        """Load entity and selector schemas from YAML files"""
        entities_path = self.schema_dir / "entities.yaml"
        selectors_path = self.schema_dir / "selectors.yaml"

        if not entities_path.exists():
            raise FileNotFoundError(f"Entities schema not found: {entities_path}")
        if not selectors_path.exists():
            raise FileNotFoundError(f"Selectors schema not found: {selectors_path}")

        with open(entities_path, 'r', encoding='utf-8') as f:
            self.entities_schema = yaml.safe_load(f)

        with open(selectors_path, 'r', encoding='utf-8') as f:
            self.selectors_schema = yaml.safe_load(f)

        logger.info("Schemas loaded successfully")

    def detect_page_type(self, url: str, soup: BeautifulSoup) -> Optional[str]:
        """
        Detect the type of page based on URL patterns and HTML content.

        Args:
            url: The page URL
            soup: BeautifulSoup object of the page

        Returns:
            Page type string or None if not detected
        """
        detection_rules = self.selectors_schema.get('page_type_detection', {})

        for page_type, rules in detection_rules.items():
            # Check URL pattern
            url_pattern = rules.get('url_pattern')
            if url_pattern and re.match(url_pattern, url):
                return page_type

            # Check meta patterns
            meta_patterns = rules.get('meta_patterns', [])
            for meta_rule in meta_patterns:
                selector = meta_rule.get('selector')
                attribute = meta_rule.get('attribute')
                expected_value = meta_rule.get('value')

                element = soup.select_one(selector)
                if element:
                    actual_value = element.get(attribute, '').lower()
                    if expected_value.lower() in actual_value:
                        return page_type

            # Check body class patterns
            body_classes = rules.get('body_class_patterns', [])
            body = soup.find('body')
            if body:
                classes = body.get('class', [])
                for pattern in body_classes:
                    if any(pattern.lower() in c.lower() for c in classes):
                        return page_type

        return None

    def extract_field(self, soup: BeautifulSoup, field_config: Dict, url: str = "") -> Any:
        """
        Extract a single field value based on selector configuration.

        Args:
            soup: BeautifulSoup object
            field_config: Field configuration from selectors schema
            url: Page URL (for URL-based extraction)

        Returns:
            Extracted value or fallback
        """
        method = field_config.get('method', 'text')
        selectors = field_config.get('selectors', [])
        fallback = field_config.get('fallback')
        pattern = field_config.get('pattern')
        field_type = field_config.get('type', 'string')

        # Handle special methods
        if method == 'from_url':
            return self._extract_from_url(url, field_config)

        if method == 'canonical_url':
            return self._extract_canonical_url(soup)

        if method == 'json_ld':
            return self._extract_json_ld(soup, field_config)

        # Try each selector in order
        value = None
        for selector_config in selectors:
            if isinstance(selector_config, dict):
                selector = selector_config.get('selector')
                sel_method = selector_config.get('method', method)
                attribute = selector_config.get('attribute')
            else:
                selector = selector_config
                sel_method = method
                attribute = field_config.get('attribute')

            if not selector:
                continue

            # Extract value based on method
            if sel_method == 'text':
                element = soup.select_one(selector)
                if element:
                    value = self._clean_text(element.get_text())

            elif sel_method == 'html':
                element = soup.select_one(selector)
                if element:
                    value = str(element)

            elif sel_method == 'attribute' or attribute:
                element = soup.select_one(selector)
                if element and attribute:
                    value = element.get(attribute, '')

            elif sel_method == 'text_list':
                elements = soup.select(selector)
                value = [self._clean_text(el.get_text()) for el in elements]
                value = [v for v in value if v]  # Remove empty strings

            elif sel_method == 'list':
                elements = soup.select(selector)
                if attribute:
                    value = [el.get(attribute, '') for el in elements]
                    value = [v for v in value if v]

            elif sel_method == 'exists':
                element = soup.select_one(selector)
                value = element is not None

            # If we got a value, break and track the hit
            if value is not None and value != '' and value != []:
                # Track selector hit (field_name will need to be passed from extract_entity)
                # For now, just track the selector itself
                selector_key = selector if isinstance(selector, str) else selector_config.get('selector', 'unknown')
                self.selector_hits[selector_key] = self.selector_hits.get(selector_key, 0) + 1
                break

        # Apply pattern extraction if specified
        if value and pattern:
            value = self._apply_pattern(value, pattern)

        # Convert to appropriate type
        if value is not None:
            value = self._convert_type(value, field_type)
        else:
            value = fallback

        return value

    def _extract_from_url(self, url: str, config: Dict) -> Optional[str]:
        """Extract value from URL using regex pattern"""
        pattern = config.get('pattern')
        group = config.get('group', 0)

        if not pattern:
            return None

        match = re.search(pattern, url)
        if match:
            return match.group(group)
        return None

    def _extract_canonical_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract canonical URL from link tag"""
        link = soup.select_one('link[rel="canonical"]')
        if link:
            return link.get('href')
        return None

    def _extract_json_ld(self, soup: BeautifulSoup, config: Dict) -> Optional[Dict]:
        """Extract and parse JSON-LD structured data"""
        selector = config.get('selector', 'script[type="application/ld+json"]')
        schema_types = config.get('schema_types', [])

        scripts = soup.select(selector)
        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle @graph arrays
                if isinstance(data, dict) and '@graph' in data:
                    data = data['@graph']

                # If data is a list, filter by schema type
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') in schema_types:
                            return item
                elif isinstance(data, dict):
                    if data.get('@type') in schema_types:
                        return data
            except (json.JSONDecodeError, AttributeError):
                continue

        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""

        # Strip whitespace
        text = text.strip()

        # Normalize spaces
        text = re.sub(r'\s+', ' ', text)

        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)

        return text

    def _apply_pattern(self, value: Union[str, List], pattern: str) -> Union[str, List]:
        """Apply regex pattern to extract specific part of value"""
        if isinstance(value, list):
            return [self._apply_pattern(v, pattern) for v in value if v]

        if not isinstance(value, str):
            return value

        match = re.search(pattern, value)
        if match:
            return match.group(1) if match.groups() else match.group(0)
        return value

    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type"""
        if value is None or value == '':
            return None

        try:
            if target_type == 'integer':
                # Remove commas from numbers
                if isinstance(value, str):
                    value = value.replace(',', '')
                return int(float(value))

            elif target_type == 'float':
                if isinstance(value, str):
                    value = value.replace(',', '')
                return float(value)

            elif target_type == 'boolean':
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1')
                return bool(value)

            elif target_type == 'date' or target_type == 'datetime':
                # Try to parse datetime
                if isinstance(value, str):
                    # Handle ISO format
                    try:
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                return value

            elif target_type == 'array':
                if not isinstance(value, list):
                    return [value] if value else []
                return value

            elif target_type == 'url':
                return str(value).strip()

            elif target_type == 'email':
                return str(value).strip().lower()

        except (ValueError, TypeError):
            return value

        return value

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug"""
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
        return re.sub(r"-{2,}", "-", text)

    def _derive_slug(self, canonical_url: str, title: str) -> str:
        """Derive a unique slug from canonical URL or title"""
        path = ""
        try:
            path = urlparse(canonical_url or "").path
        except Exception:
            pass
        segs = [s for s in path.split("/") if s]
        # Remove noisy/date segments
        drop = re.compile(r"(uk|en|blog|category|tag|page|\d{1,2}|\d{4})$", re.I)
        filtered = [s for s in segs if not drop.fullmatch(s)]
        if filtered:
            cand = filtered[-1].lower()
            if not re.fullmatch(r"\d{4}", cand):
                return cand
        if title:
            cand = self._slugify(title)
            if cand:
                return cand
        h = hashlib.sha1((canonical_url or title or "x").encode("utf-8")).hexdigest()[:8]
        return f"post-{h}"

    def extract_entity(self, page_type: str, soup: BeautifulSoup, url: str, html_path: str) -> Dict:
        """
        Extract entity data from a page.

        Args:
            page_type: Type of page (practitioner, clinic, blog_post, etc.)
            soup: BeautifulSoup object of the page
            url: Page URL
            html_path: Path to HTML file

        Returns:
            Dictionary of extracted entity data
        """
        selectors = self.selectors_schema.get(page_type, {})
        entity_data = {}

        # Extract each field
        for field_name, field_config in selectors.items():
            if field_name in ('container', 'structured_data'):
                continue

            try:
                value = self.extract_field(soup, field_config, url)
                entity_data[field_name] = value
            except Exception as e:
                logger.warning(f"Error extracting {field_name} from {url}: {e}")
                entity_data[field_name] = field_config.get('fallback')

        # Special handling for blog_post slug
        if page_type == 'blog_post':
            # Use improved slug derivation to eliminate duplicates
            entity_data['slug'] = self._derive_slug(
                entity_data.get('canonical_url') or url,
                entity_data.get('title', '')
            )

        # Add extraction metadata
        entity_data['extracted_at'] = datetime.now().isoformat()
        entity_data['source_file'] = str(html_path)

        return entity_data

    def extract_reviews(self, soup: BeautifulSoup, entity_id: str, entity_type: str) -> List[Dict]:
        """
        Extract reviews from a practitioner or clinic page.

        Args:
            soup: BeautifulSoup object of the page
            entity_id: ID of the entity being reviewed
            entity_type: Type of entity (practitioner or clinic)

        Returns:
            List of review dictionaries
        """
        review_config = self.selectors_schema.get('review', {})
        container_selector = review_config.get('container', {}).get('selector', 'div.review')

        reviews = []
        review_containers = soup.select(container_selector)

        for idx, container in enumerate(review_containers):
            review_data = {
                'reviewed_entity_type': entity_type,
                'reviewed_entity_id': entity_id,
                'extracted_at': datetime.now().isoformat()
            }

            # Extract each review field
            for field_name, field_config in review_config.items():
                if field_name == 'container':
                    continue

                try:
                    # Create a temporary soup for this container
                    temp_soup = BeautifulSoup(str(container), 'lxml')
                    value = self.extract_field(temp_soup, field_config)
                    review_data[field_name] = value
                except Exception as e:
                    logger.debug(f"Error extracting review field {field_name}: {e}")
                    review_data[field_name] = field_config.get('fallback')

            # Generate review ID if not found
            if not review_data.get('review_id'):
                review_data['review_id'] = f"{entity_id}_review_{idx}"

            reviews.append(review_data)

        return reviews

    def process_file(self, html_path: Path) -> Optional[Dict]:
        """
        Process a single HTML file and extract data.

        Args:
            html_path: Path to HTML file

        Returns:
            Dictionary containing entity data and reviews, or None if not processable
        """
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            logger.error(f"Error reading {html_path}: {e}")
            return None

        soup = BeautifulSoup(html_content, 'lxml')

        # Get URL from file (reconstruct or extract from canonical)
        url = self._extract_canonical_url(soup)
        if not url:
            # Reconstruct from file path (works for both raw and rendered)
            if 'rendered' in str(html_path):
                rel_path = html_path.relative_to(self.mirror_dir / 'rendered')
            else:
                rel_path = html_path.relative_to(self.mirror_dir / 'raw')
            url = f"https://{rel_path.parent}".replace(os.sep, '/')

        # Detect page type
        page_type = self.detect_page_type(url, soup)
        if not page_type:
            logger.debug(f"Could not detect page type for {url}")
            return None

        logger.info(f"Processing {page_type}: {url}")

        # Extract entity data
        entity_data = self.extract_entity(page_type, soup, url, str(html_path))

        result = {
            'page_type': page_type,
            'url': url,
            'entity': entity_data
        }

        # Extract reviews if applicable
        if page_type in ('practitioner', 'clinic'):
            entity_id = entity_data.get('doctify_id')
            if entity_id:
                reviews = self.extract_reviews(soup, entity_id, page_type)
                if reviews:
                    result['reviews'] = reviews

        return result

    def process_directory(self, output_dir: str = "mirror/extracted", format: str = "jsonl"):
        """
        Process all HTML files in the mirror directory.

        Args:
            output_dir: Directory to write extracted data
            format: Output format (jsonl, json, or csv)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize output files for each entity type
        entity_files = {}
        entity_types = ['practitioner', 'clinic', 'blog_post', 'review', 'specialism']

        for entity_type in entity_types:
            if format == 'jsonl':
                file_path = output_path / f"{entity_type}.jsonl"
                entity_files[entity_type] = open(file_path, 'w', encoding='utf-8')

        # Find all HTML files - prefer rendered over raw
        rendered_dir = self.mirror_dir / 'rendered'
        raw_dir = self.mirror_dir / 'raw'

        # Get all rendered files first
        rendered_files = set(rendered_dir.rglob('*.html')) if rendered_dir.exists() else set()
        raw_files = set(raw_dir.rglob('*.html')) if raw_dir.exists() else set()

        # Create a mapping of relative paths to actual file paths (prefer rendered)
        file_mapping = {}
        for raw_file in raw_files:
            rel_path = raw_file.relative_to(raw_dir)
            file_mapping[rel_path] = raw_file

        for rendered_file in rendered_files:
            rel_path = rendered_file.relative_to(rendered_dir)
            file_mapping[rel_path] = rendered_file  # Override raw with rendered

        html_files = list(file_mapping.values())
        rendered_count = sum(1 for f in html_files if 'rendered' in str(f))
        logger.info(f"Found {len(html_files)} HTML files to process ({rendered_count} rendered, {len(html_files)-rendered_count} raw)")

        stats = {
            'total': len(html_files),
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'by_type': {},
            'slug_collisions': 0
        }

        # Track seen slugs to detect and resolve collisions
        seen_slugs = {}

        # Process each file
        for html_path in html_files:
            try:
                result = self.process_file(html_path)

                if not result:
                    stats['skipped'] += 1
                    continue

                page_type = result['page_type']
                entity_data = result['entity']

                # Handle slug collisions for blog_post
                if page_type == 'blog_post' and 'slug' in entity_data:
                    original_slug = entity_data['slug']
                    if original_slug in seen_slugs:
                        # Collision detected - append hash of URL
                        url = entity_data.get('canonical_url') or entity_data.get('source_file', '')
                        hash_suffix = hashlib.sha1(url.encode('utf-8')).hexdigest()[:8]
                        entity_data['slug'] = f"{original_slug}-{hash_suffix}"
                        stats['slug_collisions'] += 1
                        logger.debug(f"Slug collision resolved: {original_slug} -> {entity_data['slug']}")
                    seen_slugs[entity_data['slug']] = True

                # Write entity data
                if page_type in entity_files:
                    entity_files[page_type].write(json.dumps(entity_data) + '\n')
                    stats['by_type'][page_type] = stats['by_type'].get(page_type, 0) + 1

                # Write reviews if present
                if 'reviews' in result and result['reviews']:
                    for review in result['reviews']:
                        entity_files['review'].write(json.dumps(review) + '\n')
                    stats['by_type']['review'] = stats['by_type'].get('review', 0) + len(result['reviews'])

                stats['processed'] += 1

                if stats['processed'] % 10 == 0:
                    logger.info(f"Processed {stats['processed']}/{stats['total']} files...")

            except Exception as e:
                logger.error(f"Error processing {html_path}: {e}")
                stats['errors'] += 1

        # Close output files
        for f in entity_files.values():
            f.close()

        # Save selector hit report
        selector_report_path = output_path / "selector_report.json"
        with open(selector_report_path, 'w', encoding='utf-8') as f:
            json.dump(self.selector_hits, f, indent=2)
        logger.info(f"\nSelector hit report saved to: {selector_report_path}")

        # Print statistics
        logger.info("\n=== Extraction Complete ===")
        logger.info(f"Total files: {stats['total']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats['errors']}")
        if stats.get('slug_collisions', 0) > 0:
            logger.info(f"Slug collisions resolved: {stats['slug_collisions']}")
        logger.info("\nEntities extracted by type:")
        for entity_type, count in stats['by_type'].items():
            logger.info(f"  {entity_type}: {count}")


def main():
    """Main entry point for the extraction script"""
    import argparse

    parser = argparse.ArgumentParser(description='Extract structured data from Doctify site mirror')
    parser.add_argument('--schema-dir', default='schema', help='Directory containing schema files')
    parser.add_argument('--mirror-dir', default='mirror', help='Directory containing mirrored HTML files')
    parser.add_argument('--output-dir', default='mirror/extracted', help='Output directory for extracted data')
    parser.add_argument('--format', default='jsonl', choices=['jsonl', 'json', 'csv'], help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Initialize and run extractor
    extractor = DoctifyExtractor(schema_dir=args.schema_dir, mirror_dir=args.mirror_dir)
    extractor.process_directory(output_dir=args.output_dir, format=args.format)


if __name__ == '__main__':
    main()
