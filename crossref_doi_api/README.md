# Crossref DOI API Tools

A complete toolkit for registering DOIs with Crossref using CSV files. This system processes bibliography data from CSV files and registers DOIs directly with Crossref's production or sandbox environments.

## Features

- ✅ **CSV to DOI Registration**: Process CSV files and register DOIs automatically
- ✅ **In-memory XML Generation**: No temporary files created - everything in memory
- ✅ **Batch Processing**: Handle hundreds/thousands of DOIs efficiently  
- ✅ **Production & Sandbox**: Test safely before registering real DOIs
- ✅ **Conflict Detection**: Check for existing DOIs before processing
- ✅ **Retry Logic**: Automatic retry with exponential backoff
- ✅ **Progress Tracking**: Progress updates every 100 entries
- ✅ **Strong Typing**: Full mypy compliance for reliability

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install requests python-dotenv

# Create credentials file
cp .env.template .env
# Edit .env with your Crossref credentials
```

### 2. Prepare Your Data

Create a CSV file with your publications (see `CSV_FORMAT.md` for details):

```csv
doi,title,resource_url,publication_year,author_given_name,author_surname
10.48106/example.2025.001,My Article,https://example.com/article1,2025,John,Doe
```

### 3. Register DOIs

```bash
# Test in sandbox (recommended first)
python batch_doi_registration.py your_data.csv

# Register in production (creates real DOIs!)
python batch_doi_registration.py your_data.csv --production
```

## Main Scripts

### `batch_doi_registration.py` - Main DOI Registration Tool

Register DOIs from CSV files directly with Crossref.

**Basic Usage:**
```bash
python batch_doi_registration.py publications.csv
```

**Options:**
- `--sandbox` - Use sandbox environment (default)
- `--production` - Use production environment ⚠️ CREATES REAL DOIs
- `--delay SECONDS` - Delay between submissions (default: 3.0)
- `--retries NUMBER` - Max retry attempts (default: 3)
- `--verify` - Verify DOIs after registration
- `--no-conflict-check` - Skip checking for existing DOIs

**Examples:**
```bash
# Safe testing in sandbox
python batch_doi_registration.py data.csv --delay 2.0

# Production with verification
python batch_doi_registration.py data.csv --production --verify

# High volume processing
python batch_doi_registration.py large_dataset.csv --delay 1.0 --retries 5
```

### `csv_to_xml.py` - Standalone XML Generation

Generate Crossref XML files from CSV (for testing/inspection).

```bash
python csv_to_xml.py publications.csv -o output_directory
```

### `xml_parser_test.py` - XML Validation

Validate XML files against Crossref requirements.

```bash
python xml_parser_test.py generated_file.xml
```

### `api_test.py` - API Testing & Exploration

Test Crossref API connectivity and explore your account.

```bash
python api_test.py
```

## Configuration

### Environment Variables (.env)

```bash
# Production credentials
CROSSREF_USERNAME=your_username
CROSSREF_PASSWORD=your_password  
CROSSREF_MEMBER_ID=your_member_id

# Sandbox credentials (optional, fallback to production)
CROSSREF_SANDBOX_USERNAME=sandbox_username
CROSSREF_SANDBOX_PASSWORD=sandbox_password
```

### CSV Format

See `CSV_FORMAT.md` for complete specification. Minimum required fields:

- `doi` - DOI to register (e.g., "10.48106/example.2025.001")
- `title` - Publication title
- `resource_url` - URL where publication is accessible
- `publication_year` - Year (YYYY format)
- `author_given_name` - First name of primary author
- `author_surname` - Last name of primary author

## Workflow

1. **Prepare CSV** with publication metadata
2. **Test in sandbox** to ensure everything works
3. **Get sandbox credentials** from Crossref support if needed
4. **Run production registration** when ready
5. **Verify DOIs** resolve correctly

## Memory-Efficient Design

The system uses Python generators to process large CSV files without loading everything into memory:

- ✅ **No temporary XML files created**
- ✅ **Streaming CSV processing**  
- ✅ **Memory usage scales with single row, not dataset size**
- ✅ **Progress reporting every 100 entries**

Perfect for processing thousands of DOIs efficiently.

## Safety Features

- **Sandbox by default** - prevents accidental production registrations
- **Production confirmation** - requires typing "YES" for production
- **Conflict checking** - prevents duplicate DOI registration  
- **Rate limiting** - respects Crossref API limits
- **Comprehensive error handling** - graceful failure recovery


## Architecture

```
CSV File → Generator → XML (in memory) → Crossref API → DOI Registration
    ↓                                           ↓
Validation                               Response Handling
    ↓                                           ↓  
Error Reporting                         Progress Tracking
```

## Troubleshooting

**"Missing credentials"**
- Ensure `.env` file exists with valid Crossref credentials

**"401 Unauthorized in sandbox"**
- Request sandbox access from Crossref support
- Use `--production` flag to test with production credentials (careful!)

**"DOI conflicts found"**
- Review existing DOIs in your account
- Use `--no-conflict-check` to override (not recommended)

**"Rate limiting errors"**  
- Increase `--delay` parameter
- Reduce concurrent processing

## Support

- 📧 Crossref Support: `support@crossref.org`
- 📖 CSV Format: See `CSV_FORMAT.md`
- 🔧 API Details: See `api_test.py`

---

**⚠️ Important**: Always test in sandbox before production registration. Production DOI registration is permanent and cannot be undone!