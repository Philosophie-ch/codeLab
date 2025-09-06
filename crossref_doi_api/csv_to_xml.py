"""
CSV to Crossref XML Generator

This script converts a CSV file containing publication data into individual 
Crossref XML files for DOI registration.

CSV Format Requirements:
=======================

Required Headers:
- doi: The DOI to register (e.g., "10.48106/test.2025.001")
- title: Article/publication title
- resource_url: URL where the publication can be accessed
- publication_year: Year of publication (YYYY format)
- author_given_name: First name of primary author
- author_surname: Last name of primary author

Optional Headers:
- subtitle: Article subtitle
- journal_title: Journal name (defaults to "Philosophie.ch Publications")
- journal_issn: Journal ISSN (defaults to "1234-5678")
- volume: Journal volume number
- issue: Journal issue number
- first_page: Starting page number
- last_page: Ending page number
- publication_month: Month of publication (1-12)
- publication_day: Day of publication (1-31)
- language: Publication language (ISO 639-1 code, defaults to "en")
- abstract: Article abstract/summary
- keywords: Comma-separated keywords
- additional_authors: JSON array of additional authors with given_name and surname

Example CSV:
===========
doi,title,resource_url,publication_year,author_given_name,author_surname,journal_title,volume,issue,first_page,last_page
10.48106/test.2025.001,Example Article,https://philosophie.ch/articles/001,2025,John,Doe,Philosophy Review,1,1,1,10
"""

from pathlib import Path
import csv
import json
import tempfile
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dotenv import load_dotenv

JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]


class CSVToXMLConverter:
    """Convert CSV publication data to Crossref XML files."""
    
    def __init__(self, depositor_name: str = "Philosophie.ch", 
                 depositor_email: str = "philipp.blum@philosophie.ch"):
        """
        Initialize the converter.
        
        Parameters
        ----------
        depositor_name : str
            Name of the organization depositing DOIs
        depositor_email : str  
            Email address of the depositor
        """
        self.depositor_name = depositor_name
        self.depositor_email = depositor_email
        self.required_fields = {
            'doi', 'title', 'resource_url', 'publication_year', 
            'author_given_name', 'author_surname'
        }
        self.optional_fields = {
            'subtitle', 'journal_title', 'journal_issn', 'volume', 'issue',
            'first_page', 'last_page', 'publication_month', 'publication_day',
            'language', 'abstract', 'keywords', 'additional_authors'
        }
        
    def validate_csv_row(self, row: Dict[str, str], row_num: int) -> List[str]:
        """
        Validate a CSV row for required fields.
        
        Parameters
        ----------
        row : Dict[str, str]
            CSV row data
        row_num : int
            Row number for error reporting
            
        Returns
        -------
        List[str]
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in row or not row[field].strip():
                errors.append(f"Row {row_num}: Missing required field '{field}'")
        
        # Validate data types and formats
        if 'publication_year' in row and row['publication_year']:
            try:
                year = int(row['publication_year'])
                if year < 1000 or year > 9999:
                    errors.append(f"Row {row_num}: Invalid year format '{row['publication_year']}'")
            except ValueError:
                errors.append(f"Row {row_num}: Year must be a number")
        
        # Validate DOI format
        if 'doi' in row and row['doi']:
            doi = row['doi'].strip()
            if not doi.startswith('10.'):
                errors.append(f"Row {row_num}: DOI must start with '10.' (got: '{doi}')")
                
        # Validate URL format
        if 'resource_url' in row and row['resource_url']:
            url = row['resource_url'].strip()
            if not (url.startswith('http://') or url.startswith('https://')):
                errors.append(f"Row {row_num}: Invalid URL format '{url}'")
        
        return errors
    
    def parse_additional_authors(self, authors_json: str) -> List[Dict[str, str]]:
        """
        Parse additional authors from JSON string.
        
        Parameters
        ----------
        authors_json : str
            JSON string containing author data
            
        Returns
        -------
        List[Dict[str, str]]
            List of author dictionaries with given_name and surname
        """
        if not authors_json.strip():
            return []
            
        try:
            authors = json.loads(authors_json)
            if not isinstance(authors, list):
                return []
            
            parsed_authors = []
            for author in authors:
                if isinstance(author, dict) and 'given_name' in author and 'surname' in author:
                    parsed_authors.append({
                        'given_name': str(author['given_name']).strip(),
                        'surname': str(author['surname']).strip()
                    })
            return parsed_authors
        except (json.JSONDecodeError, KeyError, TypeError):
            return []
    
    def generate_xml(self, row_data: Dict[str, str], batch_id: str) -> str:
        """
        Generate Crossref XML for a single publication.
        
        Parameters
        ----------
        row_data : Dict[str, str]
            Publication data from CSV row
        batch_id : str
            Unique batch identifier
            
        Returns
        -------
        str
            Generated XML content
        """
        # Set defaults
        defaults = {
            'journal_title': 'Philosophie.ch Publications',
            'journal_issn': '1234-5678',
            'language': 'en'
        }
        
        # Merge row data with defaults
        data = {**defaults, **{k: v.strip() for k, v in row_data.items() if v.strip()}}
        
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Parse additional authors
        additional_authors = []
        if 'additional_authors' in data:
            additional_authors = self.parse_additional_authors(data['additional_authors'])
        
        # Build XML
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<doi_batch version="4.4.2" xmlns="http://www.crossref.org/schema/4.4.2"',
            '           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '           xsi:schemaLocation="http://www.crossref.org/schema/4.4.2',
            '           http://www.crossref.org/schema/deposit/crossref4.4.2.xsd">',
            '',
            '  <head>',
            f'    <doi_batch_id>{batch_id}</doi_batch_id>',
            f'    <timestamp>{timestamp}</timestamp>',
            '    <depositor>',
            f'      <depositor_name>{self.depositor_name}</depositor_name>',
            f'      <email_address>{self.depositor_email}</email_address>',
            '    </depositor>',
            f'    <registrant>{self.depositor_name}</registrant>',
            '  </head>',
            '',
            '  <body>',
            '    <journal>',
            f'      <journal_metadata language="{data["language"]}">',
            f'        <full_title>{self._escape_xml(data["journal_title"])}</full_title>',
            f'        <issn media_type="electronic">{data["journal_issn"]}</issn>',
            '      </journal_metadata>',
            ''
        ]
        
        # Add journal issue if volume/issue specified
        if 'volume' in data or 'issue' in data:
            xml_lines.extend([
                '      <journal_issue>',
                '        <publication_date media_type="online">',
                f'          <year>{data["publication_year"]}</year>'
            ])
            
            if 'publication_month' in data:
                xml_lines.append(f'          <month>{data["publication_month"]}</month>')
            if 'publication_day' in data:
                xml_lines.append(f'          <day>{data["publication_day"]}</day>')
                
            xml_lines.append('        </publication_date>')
            
            if 'volume' in data:
                xml_lines.extend([
                    '        <journal_volume>',
                    f'          <volume>{data["volume"]}</volume>',
                    '        </journal_volume>'
                ])
            
            if 'issue' in data:
                xml_lines.append(f'        <issue>{data["issue"]}</issue>')
                
            xml_lines.append('      </journal_issue>')
            xml_lines.append('')
        
        # Add article data
        xml_lines.extend([
            '      <journal_article publication_type="full_text">',
            '        <titles>',
            f'          <title>{self._escape_xml(data["title"])}</title>'
        ])
        
        if 'subtitle' in data:
            xml_lines.append(f'          <subtitle>{self._escape_xml(data["subtitle"])}</subtitle>')
            
        xml_lines.append('        </titles>')
        
        # Add contributors
        xml_lines.append('        <contributors>')
        xml_lines.extend([
            '          <person_name sequence="first" contributor_role="author">',
            f'            <given_name>{self._escape_xml(data["author_given_name"])}</given_name>',
            f'            <surname>{self._escape_xml(data["author_surname"])}</surname>',
            '          </person_name>'
        ])
        
        # Add additional authors
        for author in additional_authors:
            xml_lines.extend([
                '          <person_name sequence="additional" contributor_role="author">',
                f'            <given_name>{self._escape_xml(author["given_name"])}</given_name>',
                f'            <surname>{self._escape_xml(author["surname"])}</surname>',
                '          </person_name>'
            ])
        
        xml_lines.append('        </contributors>')
        
        # Add publication date
        xml_lines.extend([
            '        <publication_date media_type="online">',
            f'          <year>{data["publication_year"]}</year>'
        ])
        
        if 'publication_month' in data:
            xml_lines.append(f'          <month>{data["publication_month"]}</month>')
        if 'publication_day' in data:
            xml_lines.append(f'          <day>{data["publication_day"]}</day>')
            
        xml_lines.append('        </publication_date>')
        
        # Add pages if specified
        if 'first_page' in data or 'last_page' in data:
            xml_lines.append('        <pages>')
            if 'first_page' in data:
                xml_lines.append(f'          <first_page>{data["first_page"]}</first_page>')
            if 'last_page' in data:
                xml_lines.append(f'          <last_page>{data["last_page"]}</last_page>')
            xml_lines.append('        </pages>')
        
        # Add DOI data
        xml_lines.extend([
            '        <doi_data>',
            f'          <doi>{data["doi"]}</doi>',
            f'          <resource>{data["resource_url"]}</resource>',
            '        </doi_data>',
            '      </journal_article>',
            '',
            '    </journal>',
            '  </body>',
            '</doi_batch>'
        ])
        
        return '\n'.join(xml_lines)
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
    
    def process_csv(self, csv_file: Union[str, Path], 
                   output_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Process CSV file and generate XML files.
        
        Parameters
        ----------
        csv_file : str or Path
            Path to input CSV file
        output_dir : str or Path, optional
            Directory to save XML files (defaults to temp directory)
            
        Returns
        -------
        Dict[str, Any]
            Processing results with statistics and file paths
        """
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="crossref_xml_"))
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        results: Dict[str, Any] = {
            'success': True,
            'total_rows': 0,
            'processed': 0,
            'errors': [],
            'xml_files': [],
            'output_directory': str(output_dir),
            'batch_id': f"philosophie-batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        }
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Validate headers
                missing_headers = self.required_fields - set(reader.fieldnames or [])
                if missing_headers:
                    results['success'] = False
                    errors_list = results['errors']
                    if isinstance(errors_list, list):
                        errors_list.append(f"Missing required CSV headers: {', '.join(missing_headers)}")
                    return results
                
                # Process rows
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    total_rows = results['total_rows']
                    if isinstance(total_rows, int):
                        results['total_rows'] = total_rows + 1
                    
                    # Validate row
                    row_errors = self.validate_csv_row(row, row_num)
                    if row_errors:
                        errors_list = results['errors']
                        if isinstance(errors_list, list):
                            errors_list.extend(row_errors)
                        continue
                    
                    try:
                        # Generate XML
                        batch_id = results['batch_id']
                        if isinstance(batch_id, str):
                            xml_content = self.generate_xml(row, batch_id)
                            
                            # Save to file
                            doi_safe = row['doi'].replace('/', '_').replace('.', '_')
                            xml_filename = f"{doi_safe}.xml"
                            xml_path = output_dir / xml_filename
                            
                            with open(xml_path, 'w', encoding='utf-8') as xml_file:
                                xml_file.write(xml_content)
                            
                            xml_files = results['xml_files']
                            if isinstance(xml_files, list):
                                xml_files.append(str(xml_path))
                            
                            processed = results['processed']
                            if isinstance(processed, int):
                                results['processed'] = processed + 1
                        
                    except Exception as e:
                        errors_list = results['errors']
                        if isinstance(errors_list, list):
                            errors_list.append(f"Row {row_num}: Error generating XML: {e}")
                        
        except Exception as e:
            results['success'] = False
            errors_list = results['errors']
            if isinstance(errors_list, list):
                errors_list.append(f"Error reading CSV file: {e}")
        
        errors_list = results['errors']
        if isinstance(errors_list, list) and errors_list:
            results['success'] = False
            
        return results


def main():
    """Main function for command-line usage."""
    load_dotenv()
    
    import argparse
    parser = argparse.ArgumentParser(
        description="Convert CSV publication data to Crossref XML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('csv_file', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output directory (default: temp directory)')
    parser.add_argument('--depositor-name', default='Philosophie.ch', 
                       help='Depositor organization name')
    parser.add_argument('--depositor-email', default='philipp.blum@philosophie.ch',
                       help='Depositor email address')
    
    args = parser.parse_args()
    
    # Create converter
    converter = CSVToXMLConverter(
        depositor_name=args.depositor_name,
        depositor_email=args.depositor_email
    )
    
    print("🔄 Processing CSV file...")
    print(f"   Input: {args.csv_file}")
    
    # Process CSV
    results = converter.process_csv(args.csv_file, args.output)
    
    # Display results
    print(f"\n📊 Processing Results:")
    print(f"   Total rows: {results['total_rows']}")
    print(f"   Successfully processed: {results['processed']}")
    print(f"   Errors: {len(results['errors'])}")
    print(f"   Output directory: {results['output_directory']}")
    print(f"   Batch ID: {results['batch_id']}")
    
    if results['xml_files']:
        print(f"\n📁 Generated XML files:")
        for xml_file in results['xml_files'][:5]:  # Show first 5
            print(f"   - {Path(xml_file).name}")
        if len(results['xml_files']) > 5:
            print(f"   ... and {len(results['xml_files']) - 5} more files")
    
    if results['errors']:
        print(f"\n❌ Errors encountered:")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(results['errors']) > 10:
            print(f"   ... and {len(results['errors']) - 10} more errors")
    
    if results['success']:
        print(f"\n✅ Processing completed successfully!")
        print(f"XML files are ready for Crossref submission.")
    else:
        print(f"\n❌ Processing completed with errors.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())