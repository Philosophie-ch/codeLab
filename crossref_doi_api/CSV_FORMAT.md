# CSV Format for Crossref DOI Registration

This document describes the required CSV format for the `csv_to_xml.py` script.

## Required Headers

These columns **must** be present in your CSV file:

| Header | Description | Example |
|--------|-------------|---------|
| `doi` | The DOI to register (must start with "10.") | `10.48106/example.2025.001` |
| `title` | Article/publication title | `The Nature of Philosophical Inquiry` |
| `resource_url` | URL where publication can be accessed | `https://philosophie.ch/articles/001` |
| `publication_year` | Year of publication (YYYY format) | `2025` |
| `author_given_name` | First name of primary author | `Johann` |
| `author_surname` | Last name of primary author | `Mueller` |

## Optional Headers

These columns are optional but provide additional metadata:

| Header | Description | Example | Default |
|--------|-------------|---------|---------|
| `subtitle` | Article subtitle | `A Modern Perspective` | _(none)_ |
| `journal_title` | Journal name | `Philosophy Quarterly` | `Philosophie.ch Publications` |
| `journal_issn` | Journal ISSN | `1234-5678` | `1234-5678` |
| `volume` | Journal volume number | `15` | _(none)_ |
| `issue` | Journal issue number | `2` | _(none)_ |
| `first_page` | Starting page number | `45` | _(none)_ |
| `last_page` | Ending page number | `62` | _(none)_ |
| `publication_month` | Month (1-12) | `3` | _(none)_ |
| `publication_day` | Day (1-31) | `15` | _(none)_ |
| `language` | Language code (ISO 639-1) | `en`, `de`, `fr` | `en` |
| `abstract` | Article abstract/summary | `An exploration of...` | _(none)_ |
| `keywords` | Comma-separated keywords | `philosophy, ethics, logic` | _(none)_ |
| `additional_authors` | JSON array of co-authors | See below | _(none)_ |

## Additional Authors Format

The `additional_authors` field should contain a JSON array of author objects:

```json
[
  {"given_name": "Maria", "surname": "Schmidt"},
  {"given_name": "Peter", "surname": "Weber"}
]
```

**Important**: When using additional authors in CSV, make sure to properly escape quotes:
```csv
"[{""given_name"": ""Maria"", ""surname"": ""Schmidt""}]"
```

## Example CSV File

See `example_publications.csv` for a complete example with all field types.

## Usage Examples

### Basic usage (temp directory):
```bash
python csv_to_xml.py publications.csv
```

### Specify output directory:
```bash
python csv_to_xml.py publications.csv -o /path/to/output
```

### Custom depositor information:
```bash
python csv_to_xml.py publications.csv --depositor-name "My University" --depositor-email "admin@university.edu"
```

## Validation Rules

The script will validate your CSV data:

1. **DOI format**: Must start with "10."
2. **URL format**: Must start with "http://" or "https://"
3. **Year format**: Must be a 4-digit number between 1000-9999
4. **Required fields**: Cannot be empty
5. **JSON format**: Additional authors must be valid JSON

## Output

The script generates:
- Individual XML files for each CSV row
- Files named using DOI (with safe characters): `10_48106_example_2025_001.xml`
- All files placed in specified or temporary directory
- Processing report with statistics and any errors

## Error Handling

Common errors and solutions:

| Error | Solution |
|-------|----------|
| "Missing required field" | Ensure all required columns are present and not empty |
| "Invalid DOI format" | DOI must start with "10." |
| "Invalid URL format" | URL must include http:// or https:// |
| "Invalid year format" | Year must be 4 digits (e.g., 2025) |
| "JSON decode error" | Check additional_authors JSON formatting |

## Tips

1. **Use UTF-8 encoding** for your CSV file to support special characters
2. **Test with small files first** before processing large datasets
3. **Backup your data** before processing
4. **Review generated XML** before submitting to Crossref
5. **Use the XML validation script** (`xml_parser_test.py`) to verify output