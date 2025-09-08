# DOI Update CSV Format

This document describes the CSV format for updating existing DOIs using `update_dois.py`.

## CSV Columns

| Column | Required | Description |
|--------|----------|-------------|
| `doi` | Yes | The existing DOI to update (e.g., "10.48106/dial.v8.i32.06") |
| `link` | Yes | The new URL where the DOI should point |
| `update_type` | No | Either "resource_only" or "full" (defaults to "resource_only") |

## Update Types

### Resource-Only Updates (default)
- **When to use**: When you only want to change where a DOI points to
- **What it does**: Updates the resource URL without changing any bibliographic metadata
- **Crossref requirement**: The new URL must be under the same domain as originally registered
- **CSV format**: Set `update_type` to "resource_only" or leave blank

### Full Updates
- **When to use**: When changing the primary URL or updating to a completely different domain
- **What it does**: Re-deposits the full metadata with the new resource URL
- **Note**: Requires the original publication metadata to be available
- **CSV format**: Set `update_type` to "full"

## Example CSV Files

### Resource-Only Updates (most common)
```csv
doi,link,update_type
10.48106/dial.v8.i32.06,https://www.philosophie.ch/kroener-1954c-updated,resource_only
10.48106/dial.v8.i32.07,https://www.philosophie.ch/another-article-updated,
```

### Full Updates
```csv
doi,link,update_type
10.48106/dial.v8.i32.06,https://newdomain.com/kroener-1954c,full
```

## Important Notes

1. **Domain restrictions**: Resource-only updates typically require the new URL to be under the same domain as originally registered
2. **Timing**: Updates may take time to propagate through Crossref's system
3. **Validation**: Always test with `--dry-run` first to validate your XML before submitting
4. **Metadata**: Full updates require the original metadata to be reconstructed or available

## Usage Example

```bash
# Test with dry run first
python update_dois.py updates.csv --dry-run

# Apply updates
python update_dois.py updates.csv

# Use sandbox for testing
python update_dois.py updates.csv --sandbox
```