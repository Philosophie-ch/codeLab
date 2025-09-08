"""
DOI Update Script

This script updates existing DOIs with new URLs or metadata using Crossref's 
resource-only deposit or full metadata update methods.

Key Features:
- Resource-only deposits for secondary URLs and metadata
- Full metadata updates for primary URL changes
- CSV batch processing
- Sandbox and production support
- Dry-run capability

Usage:
    python update_dois.py updates.csv [options]

CSV Format for Updates:
======================

Required Headers:
- doi: The existing DOI to update (e.g., "10.48106/example.2025.001")
- new_resource_url: New primary URL (requires full update)

Optional Headers:
- update_type: "resource-only" or "full" (auto-detected if not specified)
- secondary_urls: JSON array of additional URLs
- update_reason: Reason for the update (for logging)

Examples:
=========

# Update primary URL (requires full metadata update)
doi,new_resource_url,update_reason
10.48106/example.2025.001,https://newdomain.com/article1,Domain migration

# Add secondary URLs (resource-only deposit)
doi,secondary_urls,update_type
10.48106/example.2025.001,"[{\"url\": \"https://mirror.com/article1\", \"type\": \"mirror\"}]",resource-only

Limitations:
============
- Primary URL changes require full metadata redeposit
- Resource-only deposits can only add secondary URLs, not change primary URL
- All updates require existing DOI metadata to be available
"""

from pathlib import Path
import csv
import json
import tempfile
import time
from typing import Dict, Any, List, Optional, Union, Generator, Tuple
from datetime import datetime
import os
import sys
import argparse
import requests
from dotenv import load_dotenv

# Import our existing modules
from api_test import list_existing_dois
from batch_doi_registration import deposit_xml_content

JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]


class DOIUpdater:
    """Handle DOI updates using Crossref resource-only or full deposits."""
    
    def __init__(self, 
                 username: str, 
                 password: str,
                 sandbox_username: Optional[str] = None,
                 sandbox_password: Optional[str] = None,
                 depositor_name: str = "Philosophie.ch",
                 depositor_email: str = "philipp.blum@philosophie.ch"):
        """
        Initialize DOI updater.
        
        Parameters
        ----------
        username : str
            Crossref production username
        password : str
            Crossref production password
        sandbox_username : str, optional
            Crossref sandbox username (if different)
        sandbox_password : str, optional
            Crossref sandbox password (if different)
        depositor_name : str
            Organization name for XML metadata
        depositor_email : str
            Contact email for XML metadata
        """
        self.username = username
        self.password = password
        self.sandbox_username = sandbox_username or username
        self.sandbox_password = sandbox_password or password
        self.depositor_name = depositor_name
        self.depositor_email = depositor_email
        
    def get_existing_doi_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Fetch existing DOI metadata from Crossref API.
        
        Parameters
        ----------
        doi : str
            DOI to fetch metadata for
            
        Returns
        -------
        Optional[Dict[str, Any]]
            DOI metadata if found, None otherwise
        """
        try:
            response = requests.get(
                f"https://api.crossref.org/works/{doi}",
                headers={"Accept": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {})
            else:
                print(f"   ⚠️  Could not fetch metadata for {doi}: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"   ❌ Error fetching metadata for {doi}: {e}")
            return None
    
    def generate_resource_only_xml(self, doi: str, secondary_urls: List[Dict[str, str]], 
                                  batch_id: str) -> str:
        """
        Generate resource-only deposit XML for secondary URLs.
        
        Parameters
        ----------
        doi : str
            DOI to update
        secondary_urls : List[Dict[str, str]]
            List of secondary URLs with type information
        batch_id : str
            Unique batch identifier
            
        Returns
        -------
        str
            Generated resource-only XML
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<doi_batch version="5.4.0" xmlns="http://www.crossref.org/doi_resources_schema/5.4.0"',
            '           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '           xsi:schemaLocation="http://www.crossref.org/doi_resources_schema/5.4.0',
            '           http://www.crossref.org/schema/deposit/doi_resources5.4.0.xsd">',
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
            '    <doi_citations>',
            f'      <doi>{doi}</doi>',
            '      <resource>'
        ]
        
        # Add secondary URLs
        for url_info in secondary_urls:
            url = url_info.get('url', '')
            url_type = url_info.get('type', 'secondary')
            xml_lines.extend([
                f'        <resource mime_type="text/html">',
                f'          <resource_url>{self._escape_xml(url)}</resource_url>',
                f'        </resource>'
            ])
        
        xml_lines.extend([
            '      </resource>',
            '    </doi_citations>',
            '  </body>',
            '</doi_batch>'
        ])
        
        return '\n'.join(xml_lines)
    
    def generate_full_update_xml(self, doi: str, new_url: str, existing_metadata: Dict[str, Any],
                                batch_id: str) -> str:
        """
        Generate full metadata update XML with new primary URL.
        
        Parameters
        ----------
        doi : str
            DOI to update
        new_url : str
            New primary resource URL
        existing_metadata : Dict[str, Any]
            Existing DOI metadata from Crossref API
        batch_id : str
            Unique batch identifier
            
        Returns
        -------
        str
            Generated full update XML
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Extract existing metadata - use actual values only, no fake defaults
        title = existing_metadata.get('title', [''])[0] if existing_metadata.get('title') else ''
        authors = existing_metadata.get('author', [])
        pub_date = existing_metadata.get('published-print', existing_metadata.get('published-online', {}))
        year = ''
        if pub_date and pub_date.get('date-parts') and len(pub_date['date-parts']) > 0:
            year = str(pub_date['date-parts'][0][0])
        
        # Extract journal metadata
        container_title = existing_metadata.get('container-title', [''])
        journal_title = container_title[0] if container_title else ''
        issn_info = existing_metadata.get('ISSN', [])
        journal_issn = issn_info[0] if issn_info else ''
        
        # Build basic XML structure
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<doi_batch version="5.4.0" xmlns="http://www.crossref.org/schema/5.4.0"',
            '           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '           xsi:schemaLocation="http://www.crossref.org/schema/5.4.0',
            '           http://www.crossref.org/schema/deposit/crossref5.4.0.xsd">',
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
            '      <journal_metadata language="en">',
            f'        <full_title>{self._escape_xml(journal_title) if journal_title else "Journal"}</full_title>',
            f'        <issn media_type="electronic">{journal_issn}</issn>' if journal_issn else '        <issn media_type="electronic"></issn>',
            '      </journal_metadata>',
            '',
            '      <journal_article publication_type="full_text">',
            '        <titles>',
            f'          <title>{self._escape_xml(title)}</title>',
            '        </titles>',
            '        <contributors>'
        ]
        
        # Add authors if available - only use actual data
        if authors:
            primary_author = authors[0]
            given_name = primary_author.get('given', '')
            family_name = primary_author.get('family', '')
            if given_name or family_name:  # Only add if we have real names
                xml_lines.extend([
                    '          <person_name sequence="first" contributor_role="author">',
                    f'            <given_name>{self._escape_xml(given_name)}</given_name>',
                    f'            <surname>{self._escape_xml(family_name)}</surname>',
                    '          </person_name>'
                ])
        
        xml_lines.extend([
            '        </contributors>'
        ])
        
        # Only add publication date if we have actual year data
        if year:
            xml_lines.extend([
                '        <publication_date media_type="online">',
                f'          <year>{year}</year>',
                '        </publication_date>'
            ])
        
        xml_lines.extend([
            '        <doi_data>',
            f'          <doi>{doi}</doi>',
            f'          <resource>{self._escape_xml(new_url)}</resource>',
            '        </doi_data>',
            '      </journal_article>',
            '    </journal>',
            '  </body>',
            '</doi_batch>'
        ])
        
        return '\n'.join(xml_lines)
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (str(text).replace('&', '&amp;')
                         .replace('<', '&lt;')
                         .replace('>', '&gt;')
                         .replace('"', '&quot;')
                         .replace("'", '&apos;'))
    
    def deposit_update(self, username: str, password: str, xml_content: str, 
                      doi: str, update_type: str, use_sandbox: bool = True) -> bool:
        """
        Submit update XML to Crossref.
        
        Parameters
        ----------
        username : str
            Crossref username
        password : str
            Crossref password
        xml_content : str
            XML content to submit
        doi : str
            DOI being updated
        update_type : str
            Type of update ("resource-only" or "full")
        use_sandbox : bool
            Use sandbox environment
            
        Returns
        -------
        bool
            True if update successful
        """
        if use_sandbox:
            url = "https://test.crossref.org/servlet/deposit"
            print("📝 Using SANDBOX environment")
        else:
            url = "https://doi.crossref.org/servlet/deposit"
            print("⚠️  Using PRODUCTION environment")

        try:
            xml_bytes = xml_content.encode('utf-8')
            files = {"fname": (f"{doi.replace('/', '_')}_update.xml", xml_bytes, "application/xml")}
            
            # Use different operation type for resource-only deposits
            operation = "doDOICitUpload" if update_type == "resource-only" else "doMDUpload"
            
            data = {
                "operation": operation,
                "login_id": username,
                "login_passwd": password,
            }
            
            print(f"   Submitting {update_type} update for DOI: {doi}")
            print(f"   Operation: {operation}")
            
            response = requests.post(url, data=data, files=files, timeout=30)
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Update submitted successfully!")
                print("Server response:")
                print(response.text[:500])
                return True
            else:
                print(f"   ❌ Update failed: HTTP {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Error submitting update: {e}")
            return False
    
    def process_updates(self, csv_file: Union[str, Path], 
                       use_sandbox: bool = True,
                       dry_run: bool = False,
                       delay_between_updates: float = 2.0) -> Dict[str, Any]:
        """
        Process DOI updates from CSV file.
        
        Parameters
        ----------
        csv_file : str or Path
            CSV file with update instructions
        use_sandbox : bool
            Use sandbox environment
        dry_run : bool
            Generate XML without submitting
        delay_between_updates : float
            Delay between submissions
            
        Returns
        -------
        Dict[str, Any]
            Results of update processing
        """
        csv_path = Path(csv_file)
        if not csv_path.exists():
            return {
                'success': False,
                'error': f"CSV file not found: {csv_file}",
                'results': []
            }
        
        if dry_run:
            print("🔍 Starting DOI UPDATE DRY RUN...")
        else:
            print("🔄 Starting DOI updates...")
            print(f"   Environment: {'SANDBOX' if use_sandbox else 'PRODUCTION'}")
        
        # Use appropriate credentials
        submit_username = self.sandbox_username if use_sandbox else self.username
        submit_password = self.sandbox_password if use_sandbox else self.password
        
        batch_id = f"philosophie-update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        results = []
        successful = 0
        failed = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                required_fields = {'doi'}
                if not required_fields.issubset(set(reader.fieldnames or [])):
                    return {
                        'success': False,
                        'error': "Missing required CSV header: 'doi'",
                        'results': []
                    }
                
                for i, row in enumerate(reader, 1):
                    doi = row.get('doi', '').strip()
                    new_url = row.get('new_resource_url', '').strip()
                    secondary_urls_str = row.get('secondary_urls', '').strip()
                    update_type = row.get('update_type', '').strip()
                    update_reason = row.get('update_reason', 'URL update').strip()
                    
                    if not doi:
                        print(f"   [{i}] Skipping row: missing DOI")
                        continue
                    
                    print(f"\n   [{i}] Processing DOI: {doi}")
                    print(f"      Reason: {update_reason}")
                    
                    # Determine update type
                    if not update_type:
                        if new_url:
                            update_type = "full"
                        elif secondary_urls_str:
                            update_type = "resource-only"
                        else:
                            print(f"      ❌ No update data provided")
                            failed += 1
                            results.append({
                                'doi': doi,
                                'success': False,
                                'error': 'No update data provided'
                            })
                            continue
                    
                    print(f"      Update type: {update_type}")
                    
                    try:
                        if update_type == "resource-only":
                            # Parse secondary URLs
                            secondary_urls = []
                            if secondary_urls_str:
                                try:
                                    secondary_urls = json.loads(secondary_urls_str)
                                except json.JSONDecodeError:
                                    print(f"      ❌ Invalid JSON in secondary_urls")
                                    failed += 1
                                    results.append({
                                        'doi': doi,
                                        'success': False,
                                        'error': 'Invalid JSON in secondary_urls'
                                    })
                                    continue
                            
                            xml_content = self.generate_resource_only_xml(doi, secondary_urls, batch_id)
                            
                        elif update_type == "full":
                            if not new_url:
                                print(f"      ❌ Full update requires new_resource_url")
                                failed += 1
                                results.append({
                                    'doi': doi,
                                    'success': False,
                                    'error': 'Full update requires new_resource_url'
                                })
                                continue
                            
                            # Fetch existing metadata
                            print(f"      📥 Fetching existing metadata...")
                            existing_metadata = self.get_existing_doi_metadata(doi)
                            if not existing_metadata:
                                print(f"      ❌ Could not fetch existing metadata")
                                failed += 1
                                results.append({
                                    'doi': doi,
                                    'success': False,
                                    'error': 'Could not fetch existing metadata'
                                })
                                continue
                            
                            xml_content = self.generate_full_update_xml(doi, new_url, existing_metadata, batch_id)
                        
                        else:
                            print(f"      ❌ Unknown update type: {update_type}")
                            failed += 1
                            results.append({
                                'doi': doi,
                                'success': False,
                                'error': f'Unknown update type: {update_type}'
                            })
                            continue
                        
                        if dry_run:
                            # Save XML file
                            safe_doi = doi.replace('/', '_').replace('.', '_')
                            xml_filename = f"{safe_doi}_update_{update_type}.xml"
                            
                            with open(xml_filename, 'w', encoding='utf-8') as xml_file:
                                xml_file.write(xml_content)
                            
                            print(f"      ✅ XML saved: {xml_filename}")
                            successful += 1
                            results.append({
                                'doi': doi,
                                'success': True,
                                'xml_file': xml_filename,
                                'update_type': update_type
                            })
                        else:
                            # Submit update
                            success = self.deposit_update(
                                submit_username, submit_password, xml_content, 
                                doi, update_type, use_sandbox
                            )
                            
                            if success:
                                successful += 1
                                print(f"      ✅ Update successful!")
                            else:
                                failed += 1
                                print(f"      ❌ Update failed")
                            
                            results.append({
                                'doi': doi,
                                'success': success,
                                'update_type': update_type,
                                'new_url': new_url if update_type == "full" else None
                            })
                            
                            # Rate limiting
                            if i < len(list(reader)):
                                time.sleep(delay_between_updates)
                    
                    except Exception as e:
                        print(f"      ❌ Error processing update: {e}")
                        failed += 1
                        results.append({
                            'doi': doi,
                            'success': False,
                            'error': str(e)
                        })
        
        except Exception as e:
            return {
                'success': False,
                'error': f"Error processing CSV: {e}",
                'results': results
            }
        
        # Summary
        total_processed = len(results)
        print(f"\n📊 Update Processing Summary:")
        print(f"   Total DOIs: {total_processed}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        if total_processed > 0:
            print(f"   Success rate: {(successful/total_processed*100):.1f}%")
        
        return {
            'success': failed == 0,
            'total_updates': total_processed,
            'successful_updates': successful,
            'failed_updates': failed,
            'results': results,
            'batch_id': batch_id
        }


def main():
    """Main function for command-line usage."""
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Update existing DOIs using Crossref resource-only or full deposits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('csv_file', help='Input CSV file with DOI update instructions')
    parser.add_argument('--sandbox', action='store_true', 
                       help='Use sandbox environment (default: True for safety)')
    parser.add_argument('--production', action='store_true',
                       help='Use PRODUCTION environment (CAUTION: updates real DOIs!)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Generate XML files without submitting to Crossref')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between updates in seconds (default: 2.0)')
    parser.add_argument('--depositor-name', default='Philosophie.ch',
                       help='Organization name for XML metadata')
    parser.add_argument('--depositor-email', default='philipp.blum@philosophie.ch',
                       help='Contact email for XML metadata')
    
    args = parser.parse_args()
    
    # Get credentials
    username = os.getenv("CROSSREF_USERNAME")
    password = os.getenv("CROSSREF_PASSWORD")
    sandbox_username = os.getenv("CROSSREF_SANDBOX_USERNAME")
    sandbox_password = os.getenv("CROSSREF_SANDBOX_PASSWORD")
    
    if not username or not password:
        print("❌ Error: Missing credentials!")
        print("Please ensure your .env file contains:")
        print("  CROSSREF_USERNAME=your_username")
        print("  CROSSREF_PASSWORD=your_password")
        return 1
    
    # Determine environment
    use_sandbox = not args.production
    
    if args.production and not args.dry_run:
        response = input("⚠️  WARNING: You are about to update DOIs in PRODUCTION! Continue? (type 'YES' to confirm): ")
        if response != 'YES':
            print("Update cancelled.")
            return 0
    
    # Create updater
    updater = DOIUpdater(
        username=username,
        password=password,
        sandbox_username=sandbox_username,
        sandbox_password=sandbox_password,
        depositor_name=args.depositor_name,
        depositor_email=args.depositor_email
    )
    
    # Process updates
    results = updater.process_updates(
        csv_file=args.csv_file,
        use_sandbox=use_sandbox,
        dry_run=args.dry_run,
        delay_between_updates=args.delay
    )
    
    # Final summary
    if results['success']:
        print(f"\n🎉 DOI updates completed successfully!")
        print(f"   Processed: {results['successful_updates']}/{results['total_updates']} DOIs")
    else:
        print(f"\n❌ DOI updates failed!")
        if 'error' in results:
            print(f"   Error: {results['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())