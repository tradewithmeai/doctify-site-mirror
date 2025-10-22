# Doctify Site Mirror - Schema Documentation

Complete documentation for the Doctify.com scraping schema, extraction pipelines, and data structures.

## Overview

This schema defines a comprehensive data extraction framework for the Doctify.com site mirror. It includes entity definitions, CSS/BeautifulSoup selectors, extraction logic, and validation rules for extracting structured healthcare provider data.

### Key Features

- **Entity-based schema**: 5 main entity types (Practitioner, Clinic, Blog Post, Review, Specialism)
- **Flexible selectors**: CSS and BeautifulSoup selectors with fallbacks
- **Automatic page type detection**: Pattern-based classification
- **Data validation**: Type checking, required fields, format validation
- **JSONL output**: Line-delimited JSON for easy processing

## Quick Start

### Prerequisites

```bash
pip install beautifulsoup4 pyyaml lxml
```

### Basic Usage

```bash
# Extract all data from HTML files
python pipelines/extract.py

# Validate extracted data
python pipelines/validate.py

# Extract with custom paths
python pipelines/extract.py --mirror-dir mirror --output-dir output

# Validate specific entity type
python pipelines/validate.py --entity-type practitioner
```

## Directory Structure

```
site-mirror/
├── schema/
│   ├── entities.yaml          # Entity definitions and field schemas
│   └── selectors.yaml         # CSS/BeautifulSoup extraction selectors
├── pipelines/
│   ├── extract.py             # Main extraction script
│   └── validate.py            # Data validation script
├── mirror/
│   ├── raw/                   # Raw HTML files
│   ├── rendered/              # Rendered HTML (if using headless browser)
│   ├── meta/                  # Crawl metadata
│   └── extracted/             # Extracted JSONL data (output)
└── README_schema.md           # This file
```

## Entity Types

### 1. Practitioner

Healthcare professionals including doctors, specialists, and consultants.

**Primary Key**: `doctify_id` (extracted from URL)

**Key Fields**:
- Basic info: `name`, `title`, `qualifications`
- Professional: `specialisms`, `registration_number`, `professional_memberships`
- Practice: `bio`, `treatments`, `conditions_treated`, `languages`
- Location: `clinics` (array of clinic associations)
- Reviews: `rating_average`, `rating_count`, `reviews`
- Metadata: `verified`, `accepts_nhs`, `accepts_private`

**Example URL**: `https://www.doctify.com/uk/specialist/dr-adam-harris`

### 2. Clinic

Healthcare facilities, practices, and hospitals.

**Primary Key**: `doctify_id` (extracted from URL)

**Key Fields**:
- Basic: `name`, `type`, `description`
- Location: `address_line1`, `city`, `postcode`, `latitude`, `longitude`
- Contact: `phone`, `email`, `website`
- Services: `specialisms`, `treatments`, `facilities`
- Accessibility: `opening_hours`, `parking_available`, `wheelchair_accessible`
- Reviews: `rating_average`, `rating_count`

**Example URL**: `https://www.doctify.com/uk/clinic/cathedral-eye-clinic`

### 3. Review

Patient reviews and ratings for practitioners or clinics.

**Primary Key**: `review_id`

**Key Fields**:
- Target: `reviewed_entity_type`, `reviewed_entity_id`
- Rating: `rating`, `rating_bedside_manner`, `rating_waiting_time`, etc.
- Content: `title`, `text`
- Reviewer: `reviewer_name`, `reviewer_initials`, `reviewer_verified`
- Treatment: `treatment_received`, `condition_treated`
- Response: `practitioner_response`, `response_date`
- Dates: `review_date`, `appointment_date`

### 4. Blog Post

Educational and informational healthcare content.

**Primary Key**: `slug` (from URL)

**Key Fields**:
- Content: `title`, `subtitle`, `excerpt`, `content`
- Classification: `categories`, `tags`
- Author: `author_name`, `author_bio`
- SEO: `meta_description`, `featured_image_url`
- Related: `related_practitioners`, `related_specialisms`
- Dates: `published_date`, `modified_date`

**Example URL**: `https://www.doctify.com/uk/blog/posts/can-laser-treatment-really-help-rosacea-heres-what-to-know`

### 5. Specialism

Medical specialisms and specialty areas.

**Primary Key**: `slug` (from URL)

**Key Fields**:
- Basic: `name`, `description`, `category`
- Metadata: `practitioner_count`, `common_treatments`, `common_conditions`

**Example URL**: `https://www.doctify.com/uk/find/dermatology/...`

## Schema Files

### entities.yaml

Defines the structure of each entity type including:

- **Fields**: Name, type, description, requirements
- **Data types**: string, integer, float, boolean, array, url, email, date, datetime
- **Validation rules**: Required fields, format validation, value constraints
- **Relationships**: One-to-many, many-to-many between entities
- **Output formats**: JSONL, JSON, CSV specifications

### selectors.yaml

Defines extraction rules including:

- **Page type detection**: URL patterns, meta tags, body classes
- **Field selectors**: Multiple CSS selector fallbacks for each field
- **Extraction methods**: text, html, attribute, text_list, exists, json_ld
- **Data cleaning**: Whitespace normalization, HTML entity decoding
- **Pattern extraction**: Regex patterns for extracting specific values

## Extraction Pipeline

### How It Works

1. **Page Type Detection**: Identifies page type based on URL pattern and HTML structure
2. **Field Extraction**: For each field, tries multiple selectors in order until value found
3. **Data Cleaning**: Normalizes text, removes unwanted characters
4. **Type Conversion**: Converts strings to appropriate types (int, float, boolean, etc.)
5. **Pattern Matching**: Applies regex patterns to extract specific parts of values
6. **Output**: Writes entities to JSONL files by type

### Extraction Methods

- **text**: Extract text content from element
- **html**: Extract HTML content preserving structure
- **attribute**: Extract specific attribute value
- **text_list**: Extract text from multiple elements into array
- **list**: Extract attribute from multiple elements into array
- **exists**: Boolean check if element exists
- **json_ld**: Parse JSON-LD structured data
- **from_url**: Extract value from URL using regex
- **canonical_url**: Get canonical URL from link tag

### Example Selector Configuration

```yaml
practitioner:
  name:
    selectors:
      - selector: "h1.practitioner-name"
        method: "text"
      - selector: "div.profile-header h1"
        method: "text"
      - selector: "span[itemprop='name']"
        method: "text"
    fallback: null

  rating_average:
    selectors:
      - selector: "[itemprop='ratingValue']"
        method: "text"
      - selector: "span.rating-value"
        method: "text"
    type: "float"
    fallback: null
```

## Validation Pipeline

The validation script checks extracted data for:

### Field Validation

- **Required fields**: All required fields must be present and non-empty
- **Data types**: Values must match specified types
- **URL format**: Valid HTTP/HTTPS URLs
- **Email format**: Valid email addresses
- **Rating range**: Rating values between 0-5
- **Enum values**: Values must be in allowed list

### Entity Validation

- **Primary key**: Must be present and unique
- **Field coverage**: Tracks which fields are populated
- **Duplicate detection**: Identifies duplicate primary keys

### Validation Report

The validator generates a comprehensive report showing:

- Total entities processed
- Valid vs invalid count and percentage
- Field coverage statistics
- Sample validation errors
- Duplicate primary key warnings

### Example Validation Output

```
======================================================================
VALIDATION REPORT
======================================================================

PRACTITIONER
----------------------------------------------------------------------
  Total entities: 127
  Valid: 115 (90.6%)
  Invalid: 12 (9.4%)

  Field coverage:
    doctify_id: 127/127 (100.0%)
    url: 127/127 (100.0%)
    name: 127/127 (100.0%)
    rating_average: 98/127 (77.2%)
    specialisms: 115/127 (90.6%)

  Sample errors (showing first 5 of 12):
    Line 42: dr-john-smith
      - Required field 'name' is missing or empty
```

## Output Format

### JSONL (JSON Lines)

Each entity is written as a single JSON object per line:

```jsonl
{"doctify_id": "dr-adam-harris", "name": "Dr Adam Harris", "specialisms": ["Dermatology"], ...}
{"doctify_id": "dr-jane-doe", "name": "Dr Jane Doe", "specialisms": ["Cardiology"], ...}
```

**Advantages**:
- Easy to stream and process line-by-line
- Append-friendly
- Works well with command-line tools (grep, awk, etc.)
- Compact and efficient

### Output Files

After extraction, you'll find these files in `mirror/extracted/`:

- `practitioner.jsonl` - Healthcare practitioners
- `clinic.jsonl` - Clinics and facilities
- `blog_post.jsonl` - Blog articles
- `review.jsonl` - Patient reviews
- `specialism.jsonl` - Medical specialisms

## Advanced Usage

### Custom Schema Directory

```bash
python pipelines/extract.py --schema-dir custom_schema
```

### Verbose Logging

```bash
python pipelines/extract.py --verbose
```

### Processing Specific File

```python
from pathlib import Path
from pipelines.extract import DoctifyExtractor

extractor = DoctifyExtractor()
result = extractor.process_file(Path("mirror/raw/www.doctify.com/uk/specialist/dr-john-smith/index.html"))
print(result)
```

### Custom Validation

```python
from pipelines.validate import DataValidator

validator = DataValidator()
is_valid, errors = validator.validate_entity(entity_data, "practitioner")
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

## Data Relationships

### Entity Relationships

```
Practitioner ←→ Clinic (many-to-many via clinic_association)
Practitioner ← Review (one-to-many)
Clinic ← Review (one-to-many)
Practitioner ←→ Specialism (many-to-many)
Clinic ←→ Specialism (many-to-many)
BlogPost ←→ Practitioner (many-to-many, extracted from links)
BlogPost ←→ Specialism (many-to-many, extracted from links)
```

### Linking Entities

Use primary keys to link entities:

```python
# Load data
practitioners = [json.loads(line) for line in open("mirror/extracted/practitioner.jsonl")]
reviews = [json.loads(line) for line in open("mirror/extracted/review.jsonl")]

# Get reviews for a specific practitioner
practitioner_id = "dr-adam-harris"
practitioner_reviews = [r for r in reviews if r['reviewed_entity_id'] == practitioner_id]
```

## Schema Extension

### Adding New Fields

1. Update `schema/entities.yaml`:

```yaml
practitioner:
  fields:
    new_field:
      type: "string"
      required: false
      description: "Description of new field"
```

2. Update `schema/selectors.yaml`:

```yaml
practitioner:
  new_field:
    selectors:
      - selector: "div.new-field"
        method: "text"
    fallback: null
```

3. Re-run extraction

### Adding New Entity Type

1. Define entity in `schema/entities.yaml`
2. Add selectors in `schema/selectors.yaml`
3. Add page type detection rules
4. Update extraction and validation scripts to include new type

## Troubleshooting

### Common Issues

**Issue**: Selectors not matching

- **Solution**: Check selector syntax in browser DevTools
- **Solution**: Add fallback selectors
- **Solution**: Enable verbose logging to see what's being matched

**Issue**: Type conversion errors

- **Solution**: Check raw HTML values
- **Solution**: Add data cleaning patterns
- **Solution**: Update type conversion logic

**Issue**: Missing required fields

- **Solution**: Review entity schema requirements
- **Solution**: Check if HTML structure changed
- **Solution**: Update selectors

### Debugging

Enable verbose logging:

```bash
python pipelines/extract.py --verbose
```

Check intermediate data:

```python
from bs4 import BeautifulSoup

with open("mirror/raw/path/to/file.html") as f:
    soup = BeautifulSoup(f, 'lxml')

# Test selector
elements = soup.select("div.practitioner-name")
print(f"Found {len(elements)} elements")
```

## Performance

### Processing Speed

- **~10-20 pages/second** on typical hardware
- **Memory usage**: ~100-200MB for typical extraction
- **Bottleneck**: HTML parsing and file I/O

### Optimization Tips

1. **Parallel processing**: Process files in parallel using multiprocessing
2. **Selective extraction**: Only extract needed entity types
3. **Incremental processing**: Track processed files to avoid re-extraction
4. **Batch processing**: Process files in batches to reduce memory usage

## Data Quality

### Field Coverage

Expected field coverage based on Doctify site structure:

| Entity | Field | Expected Coverage |
|--------|-------|------------------|
| Practitioner | name | ~100% |
| Practitioner | specialisms | ~90%+ |
| Practitioner | rating_average | ~70-80% |
| Practitioner | bio | ~60-70% |
| Clinic | address | ~95%+ |
| Blog Post | title | ~100% |
| Review | rating | ~100% |

### Data Accuracy

The schema is designed to handle:

- Multiple selector fallbacks for reliability
- Text cleaning and normalization
- Type conversion with error handling
- Pattern-based extraction for complex fields

## License and Usage

This schema and extraction framework is designed specifically for the Doctify.com site mirror project. Modify and extend as needed for your specific use case.

## Support and Contribution

### Reporting Issues

When reporting extraction or validation issues, include:

1. Page type and URL
2. Expected vs actual output
3. Relevant HTML snippet
4. Error messages or logs

### Improving Selectors

To improve selector accuracy:

1. Analyze failed extractions
2. Inspect HTML structure
3. Add fallback selectors
4. Test on representative sample
5. Update schema files
6. Re-run extraction and validation

## Version History

- **v1.0** (2025-10-22): Initial schema release
  - 5 entity types defined
  - Complete selector definitions
  - Extraction and validation pipelines
  - Comprehensive documentation

## References

### Technologies Used

- **BeautifulSoup4**: HTML parsing and CSS selector support
- **PyYAML**: Schema file parsing
- **Python 3.7+**: Core language and standard library

### Related Documentation

- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [CSS Selectors Reference](https://www.w3.org/TR/selectors/)
- [JSONL Format](http://jsonlines.org/)
- [Schema.org](https://schema.org/) - JSON-LD structured data reference

## Appendix: Complete Field List

### Practitioner Fields

```
doctify_id, url, name, title, first_name, last_name, specialisms,
qualifications, professional_memberships, registration_number, bio,
treatments, conditions_treated, languages, clinics, phone, email,
website, rating_average, rating_count, reviews, profile_image_url,
verified, accepts_nhs, accepts_private, online_booking_available,
extracted_at, last_updated, source_file
```

### Clinic Fields

```
doctify_id, url, name, type, description, address_line1, address_line2,
city, county, postcode, country, latitude, longitude, phone, email,
website, specialisms, treatments, facilities, opening_hours,
parking_available, wheelchair_accessible, rating_average, rating_count,
images, logo_url, verified, accepts_nhs, accepts_private, extracted_at,
last_updated, source_file
```

### Review Fields

```
review_id, reviewed_entity_type, reviewed_entity_id, rating, title, text,
rating_bedside_manner, rating_waiting_time, rating_staff_friendliness,
rating_cleanliness, rating_explanation, reviewer_name, reviewer_initials,
reviewer_verified, treatment_received, condition_treated,
practitioner_response, response_date, review_date, appointment_date,
extracted_at
```

### Blog Post Fields

```
slug, url, title, subtitle, excerpt, content, categories, tags,
author_name, author_bio, featured_image_url, reading_time_minutes,
word_count, meta_description, meta_keywords, related_practitioners,
related_specialisms, published_date, modified_date, extracted_at,
source_file
```

### Specialism Fields

```
slug, url, name, description, category, practitioner_count,
common_treatments, common_conditions, extracted_at
```
