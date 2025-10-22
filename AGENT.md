\# Task

Analyse the Doctify site mirror under mirror/ and design a structured scraping schema.



\# Objectives

1\. Identify page types (Practitioner, Clinic, Specialism, Review, etc.)

2\. Define entities, fields, and relationships.

3\. Build selectors and extraction logic (BeautifulSoup preferred).

4\. Validate output and generate JSONL per entity type.



\# Input Data

mirror/raw/\*\* 

mirror/rendered/\*\* 

mirror/meta/crawl\_index.jsonl 

mirror/extracted/quick\_index.jsonl



\# Deliverables

schema/entities.yaml

schema/selectors.yaml

pipelines/extract.py

pipelines/validate.py

README\_schema.md



