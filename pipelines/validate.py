#!/usr/bin/env python3
"""
Doctify Data Validation Pipeline
Validates extracted data against entity schema definitions.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import logging

try:
    import yaml
except ImportError:
    print("Missing required dependency: pyyaml")
    print("Install with: pip install pyyaml")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Validates extracted data against schema definitions"""

    def __init__(self, schema_dir: str = "schema"):
        """
        Initialize validator with schema directory.

        Args:
            schema_dir: Path to directory containing schema YAML files
        """
        self.schema_dir = Path(schema_dir)
        self.entities_schema = None
        self._load_schema()

    def _load_schema(self):
        """Load entity schema from YAML file"""
        schema_path = self.schema_dir / "entities.yaml"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        with open(schema_path, 'r', encoding='utf-8') as f:
            self.entities_schema = yaml.safe_load(f)

        logger.info("Schema loaded successfully")

    def validate_field(self, field_name: str, value: Any, field_schema: Dict) -> List[str]:
        """
        Validate a single field value against its schema.

        Args:
            field_name: Name of the field
            value: Field value
            field_schema: Schema definition for the field

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check if required field is present
        if field_schema.get('required', False):
            if value is None or value == '' or value == []:
                errors.append(f"Required field '{field_name}' is missing or empty")
                return errors

        # Skip validation for non-required null values
        if value is None and not field_schema.get('required', False):
            return errors

        # Validate data type
        field_type = field_schema.get('type', 'string')
        type_error = self._validate_type(field_name, value, field_type)
        if type_error:
            errors.append(type_error)
            return errors  # Stop further validation if type is wrong

        # Type-specific validation
        if field_type == 'url':
            if not self._is_valid_url(value):
                errors.append(f"Field '{field_name}' has invalid URL format: {value}")

        elif field_type == 'email':
            if not self._is_valid_email(value):
                errors.append(f"Field '{field_name}' has invalid email format: {value}")

        elif field_type == 'float':
            # Check rating range if applicable
            if 'rating' in field_name.lower():
                if not (0 <= value <= 5):
                    errors.append(f"Field '{field_name}' rating value {value} is out of range (0-5)")

        elif field_type == 'integer':
            if value < 0:
                errors.append(f"Field '{field_name}' has negative integer value: {value}")

        # Check enum values
        if 'enum' in field_schema:
            allowed_values = field_schema['enum']
            if value not in allowed_values:
                errors.append(
                    f"Field '{field_name}' value '{value}' not in allowed values: {allowed_values}"
                )

        return errors

    def _validate_type(self, field_name: str, value: Any, expected_type: str) -> Optional[str]:
        """
        Validate that a value matches the expected type.

        Args:
            field_name: Name of the field
            value: Value to validate
            expected_type: Expected type string

        Returns:
            Error message if type is wrong, None if correct
        """
        if expected_type == 'string':
            if not isinstance(value, str):
                return f"Field '{field_name}' expected string, got {type(value).__name__}"

        elif expected_type == 'integer':
            if not isinstance(value, int) or isinstance(value, bool):
                return f"Field '{field_name}' expected integer, got {type(value).__name__}"

        elif expected_type == 'float':
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return f"Field '{field_name}' expected float, got {type(value).__name__}"

        elif expected_type == 'boolean':
            if not isinstance(value, bool):
                return f"Field '{field_name}' expected boolean, got {type(value).__name__}"

        elif expected_type in ('array', 'array[string]'):
            if not isinstance(value, list):
                return f"Field '{field_name}' expected array, got {type(value).__name__}"

        elif expected_type == 'object':
            if not isinstance(value, dict):
                return f"Field '{field_name}' expected object, got {type(value).__name__}"

        elif expected_type in ('url', 'email', 'text', 'html'):
            # These are string subtypes
            if not isinstance(value, str):
                return f"Field '{field_name}' expected string, got {type(value).__name__}"

        elif expected_type in ('date', 'datetime'):
            # Accept strings for dates/datetimes
            if not isinstance(value, str):
                return f"Field '{field_name}' expected datetime string, got {type(value).__name__}"

        return None

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        if not isinstance(url, str):
            return False

        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(url_pattern.match(url))

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        if not isinstance(email, str):
            return False

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(email))

    def validate_entity(self, entity_data: Dict, entity_type: str) -> Tuple[bool, List[str]]:
        """
        Validate a complete entity against its schema.

        Args:
            entity_data: Dictionary of entity data
            entity_type: Type of entity (practitioner, clinic, etc.)

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Get entity schema
        entity_schema = self.entities_schema.get('entities', {}).get(entity_type)
        if not entity_schema:
            errors.append(f"Unknown entity type: {entity_type}")
            return False, errors

        field_schemas = entity_schema.get('fields', {})

        # Validate each field in the schema
        for field_name, field_schema in field_schemas.items():
            value = entity_data.get(field_name)
            field_errors = self.validate_field(field_name, value, field_schema)
            errors.extend(field_errors)

        # Check for primary key
        primary_key = entity_schema.get('primary_key')
        if primary_key:
            pk_value = entity_data.get(primary_key)
            if not pk_value:
                errors.append(f"Primary key '{primary_key}' is missing or empty")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_file(self, jsonl_path: Path, entity_type: str) -> Dict:
        """
        Validate all entities in a JSONL file.

        Args:
            jsonl_path: Path to JSONL file
            entity_type: Type of entities in the file

        Returns:
            Dictionary with validation statistics and errors
        """
        logger.info(f"Validating {entity_type} data from {jsonl_path}")

        stats = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'errors': [],
            'primary_key_duplicates': [],
            'field_coverage': defaultdict(int)
        }

        seen_keys = set()
        entity_schema = self.entities_schema.get('entities', {}).get(entity_type, {})
        primary_key = entity_schema.get('primary_key')

        if not jsonl_path.exists():
            logger.warning(f"File not found: {jsonl_path}")
            return stats

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    entity_data = json.loads(line)
                    stats['total'] += 1

                    # Track field coverage
                    for field in entity_data.keys():
                        stats['field_coverage'][field] += 1

                    # Validate entity
                    is_valid, errors = self.validate_entity(entity_data, entity_type)

                    if is_valid:
                        stats['valid'] += 1
                    else:
                        stats['invalid'] += 1
                        # Store first 100 errors to avoid memory issues
                        if len(stats['errors']) < 100:
                            stats['errors'].append({
                                'line': line_num,
                                'entity_id': entity_data.get(primary_key),
                                'errors': errors
                            })

                    # Check for duplicate primary keys
                    if primary_key:
                        pk_value = entity_data.get(primary_key)
                        if pk_value:
                            if pk_value in seen_keys:
                                stats['primary_key_duplicates'].append({
                                    'line': line_num,
                                    'key': pk_value
                                })
                            seen_keys.add(pk_value)

                except json.JSONDecodeError as e:
                    stats['invalid'] += 1
                    if len(stats['errors']) < 100:
                        stats['errors'].append({
                            'line': line_num,
                            'errors': [f"Invalid JSON: {e}"]
                        })

        return stats

    def validate_directory(self, data_dir: str = "mirror/extracted") -> Dict:
        """
        Validate all entity files in a directory.

        Args:
            data_dir: Directory containing extracted JSONL files

        Returns:
            Dictionary with validation results for all entity types
        """
        data_path = Path(data_dir)
        entity_types = ['practitioner', 'clinic', 'blog_post', 'review', 'specialism']

        results = {}

        for entity_type in entity_types:
            jsonl_file = data_path / f"{entity_type}.jsonl"
            if jsonl_file.exists():
                results[entity_type] = self.validate_file(jsonl_file, entity_type)
                # Create sample file
                self._create_sample_file(jsonl_file, data_path, entity_type)
            else:
                logger.info(f"No file found for {entity_type}, skipping")

        # Save validation report
        report_path = data_path / "validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            # Convert defaultdict to regular dict for JSON serialization
            results_serializable = {}
            for entity_type, stats in results.items():
                results_serializable[entity_type] = {
                    'total': stats['total'],
                    'valid': stats['valid'],
                    'invalid': stats['invalid'],
                    'errors': stats['errors'],
                    'primary_key_duplicates': stats['primary_key_duplicates'],
                    'field_coverage': dict(stats['field_coverage'])
                }
            json.dump(results_serializable, f, indent=2)
        logger.info(f"Validation report saved to: {report_path}")

        return results

    def _create_sample_file(self, jsonl_file: Path, output_dir: Path, entity_type: str, sample_count: int = 5):
        """Create a sample file with first N records"""
        sample_dir = output_dir / "samples"
        sample_dir.mkdir(exist_ok=True)

        sample_file = sample_dir / f"{entity_type}_sample.json"
        samples = []

        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= sample_count:
                    break
                if line.strip():
                    try:
                        samples.append(json.loads(line))
                    except:
                        pass

        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, indent=2, ensure_ascii=False)

        logger.debug(f"Created sample file: {sample_file}")

    def print_validation_report(self, results: Dict):
        """
        Print a formatted validation report.

        Args:
            results: Validation results dictionary
        """
        print("\n" + "=" * 70)
        print("VALIDATION REPORT")
        print("=" * 70 + "\n")

        overall_total = 0
        overall_valid = 0
        overall_invalid = 0

        for entity_type, stats in results.items():
            total = stats['total']
            valid = stats['valid']
            invalid = stats['invalid']

            overall_total += total
            overall_valid += valid
            overall_invalid += invalid

            print(f"\n{entity_type.upper()}")
            print("-" * 70)
            print(f"  Total entities: {total}")
            print(f"  Valid: {valid} ({100 * valid / total if total > 0 else 0:.1f}%)")
            print(f"  Invalid: {invalid} ({100 * invalid / total if total > 0 else 0:.1f}%)")

            # Print duplicate keys
            if stats['primary_key_duplicates']:
                print(f"\n  WARNING: Found {len(stats['primary_key_duplicates'])} duplicate primary keys")
                for dup in stats['primary_key_duplicates'][:5]:
                    print(f"    Line {dup['line']}: {dup['key']}")
                if len(stats['primary_key_duplicates']) > 5:
                    print(f"    ... and {len(stats['primary_key_duplicates']) - 5} more")

            # Print field coverage
            if stats['field_coverage']:
                print(f"\n  Field coverage:")
                sorted_fields = sorted(stats['field_coverage'].items(), key=lambda x: x[1], reverse=True)
                for field, count in sorted_fields[:10]:
                    coverage = 100 * count / total if total > 0 else 0
                    print(f"    {field}: {count}/{total} ({coverage:.1f}%)")

            # Print sample errors
            if stats['errors']:
                print(f"\n  Sample errors (showing first 5 of {len(stats['errors'])}):")
                for error in stats['errors'][:5]:
                    print(f"    Line {error.get('line')}: {error.get('entity_id', 'N/A')}")
                    for err_msg in error['errors'][:3]:
                        print(f"      - {err_msg}")

        # Overall summary
        print("\n" + "=" * 70)
        print("OVERALL SUMMARY")
        print("=" * 70)
        print(f"Total entities across all types: {overall_total}")
        print(f"Valid: {overall_valid} ({100 * overall_valid / overall_total if overall_total > 0 else 0:.1f}%)")
        print(f"Invalid: {overall_invalid} ({100 * overall_invalid / overall_total if overall_total > 0 else 0:.1f}%)")
        print()


def main():
    """Main entry point for the validation script"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate extracted Doctify data')
    parser.add_argument('--schema-dir', default='schema', help='Directory containing schema files')
    parser.add_argument('--data-dir', default='mirror/extracted', help='Directory containing extracted JSONL files')
    parser.add_argument('--entity-type', help='Validate specific entity type only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Initialize validator
    validator = DataValidator(schema_dir=args.schema_dir)

    # Validate data
    if args.entity_type:
        # Validate single entity type
        jsonl_file = Path(args.data_dir) / f"{args.entity_type}.jsonl"
        results = {args.entity_type: validator.validate_file(jsonl_file, args.entity_type)}
    else:
        # Validate all entity types
        results = validator.validate_directory(data_dir=args.data_dir)

    # Print report
    validator.print_validation_report(results)


if __name__ == '__main__':
    main()
