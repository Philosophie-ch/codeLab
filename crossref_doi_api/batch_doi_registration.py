"""
Batch DOI Registration from CSV

This script processes a CSV file and registers DOIs directly with Crossref.
It combines CSV processing, XML generation, and DOI submission in one workflow.

Usage:
    python batch_doi_registration.py publications.csv [options]

Features:
- Processes CSV files with publication metadata
- Generates Crossref XML for each publication
- Submits DOIs to Crossref (production or sandbox)
- Tracks submission status and provides detailed reports
- Handles errors gracefully with rollback options

Requirements:
- CSV file following the format described in CSV_FORMAT.md
- Crossref credentials in .env file
- Network connection for API submissions
"""

from pathlib import Path
import csv
import tempfile
import time
from typing import Dict, Any, List, Optional, Union
import os
import sys
import argparse
from dotenv import load_dotenv

# Import our existing modules
from csv_to_xml import CSVToXMLConverter
from api_test import list_existing_dois
import requests

JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]


def deposit_xml_content(username: str, password: str, xml_content: str, 
                       doi: str, use_sandbox: bool = True) -> bool:
    """
    Submit XML content directly to Crossref without creating a file.
    
    Parameters
    ----------
    username : str
        Crossref login username
    password : str
        Crossref login password
    xml_content : str
        XML content as string
    doi : str
        DOI being submitted (for error reporting)
    use_sandbox : bool
        Use sandbox environment if True
        
    Returns
    -------
    bool
        True if submission successful
    """
    if use_sandbox:
        url = "https://test.crossref.org/servlet/deposit"
        print("📝 Using SANDBOX environment")
    else:
        url = "https://doi.crossref.org/servlet/deposit"
        print("⚠️  Using PRODUCTION environment")

    try:
        # Create file-like object from XML string
        xml_bytes = xml_content.encode('utf-8')
        files = {"fname": (f"{doi.replace('/', '_')}.xml", xml_bytes, "application/xml")}
        
        data = {
            "operation": "doMDUpload",
            "login_id": username,
            "login_passwd": password,
        }
        
        print(f"   Attempting deposit for DOI: {doi}")
        response = requests.post(url, data=data, files=files, timeout=30)
        
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Deposit submitted successfully!")
            print("Server response:")
            print(response.text[:500])  # Show first 500 chars
            return True
        elif response.status_code == 401:
            print("❌ 401 Unauthorized - check credentials")
            return False
        else:
            print(f"   Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            
            # Check if it's just a warning/success with different code
            if "success" in response.text.lower() or "accepted" in response.text.lower():
                print("✅ Deposit appears successful despite status code!")
                return True
            
            return False
            
    except requests.RequestException as e:
        print(f"❌ Error depositing DOI: {e}")
        return False


class BatchDOIRegistration:
    """Handle batch DOI registration from CSV files."""
    
    def __init__(self, 
                 username: str, 
                 password: str,
                 sandbox_username: Optional[str] = None,
                 sandbox_password: Optional[str] = None,
                 depositor_name: str = "Philosophie.ch",
                 depositor_email: str = "philipp.blum@philosophie.ch"):
        """
        Initialize batch DOI registration.
        
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
        
        self.csv_converter = CSVToXMLConverter(depositor_name, depositor_email)
        
    def check_doi_conflicts(self, csv_file: Union[str, Path], 
                           member_id: str) -> Dict[str, Any]:
        """
        Check if any DOIs in CSV already exist in Crossref.
        
        Parameters
        ----------
        csv_file : str or Path
            CSV file to check
        member_id : str
            Crossref member ID
            
        Returns
        -------
        Dict[str, Any]
            Results with existing DOIs and conflicts
        """
        print("🔍 Checking for DOI conflicts...")
        
        # Get existing DOIs from Crossref
        try:
            existing_dois = list_existing_dois(int(member_id), rows=1000)
            existing_set = set(existing_dois)
            print(f"   Found {len(existing_dois)} existing DOIs in your account")
        except Exception as e:
            print(f"   ⚠️  Could not fetch existing DOIs: {e}")
            existing_set = set()
        
        # Get DOIs from CSV
        csv_dois = []
        conflicts = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    if 'doi' in row and row['doi'].strip():
                        doi = row['doi'].strip()
                        csv_dois.append(doi)
                        
                        if doi in existing_set:
                            conflicts.append({
                                'row': row_num,
                                'doi': doi,
                                'title': row.get('title', '(no title)')
                            })
        except Exception as e:
            return {
                'success': False,
                'error': f"Error reading CSV: {e}",
                'csv_dois': [],
                'existing_dois': list(existing_set),
                'conflicts': []
            }
        
        print(f"   CSV contains {len(csv_dois)} DOIs")
        if conflicts:
            print(f"   ⚠️  Found {len(conflicts)} DOI conflicts!")
            for conflict in conflicts[:5]:  # Show first 5
                print(f"      - Row {conflict['row']}: {conflict['doi']}")
            if len(conflicts) > 5:
                print(f"      ... and {len(conflicts) - 5} more conflicts")
        else:
            print("   ✅ No DOI conflicts found")
        
        return {
            'success': True,
            'csv_dois': csv_dois,
            'existing_dois': list(existing_set),
            'conflicts': conflicts
        }
    
    def register_batch(self, 
                      csv_file: Union[str, Path],
                      use_sandbox: bool = True,
                      check_conflicts: bool = True,
                      delay_between_submissions: float = 2.0,
                      max_retries: int = 3) -> Dict[str, Any]:
        """
        Register DOIs from CSV file in batch.
        
        Parameters
        ----------
        csv_file : str or Path
            Input CSV file
        use_sandbox : bool
            Use sandbox environment for testing
        check_conflicts : bool
            Check for existing DOI conflicts before processing
        delay_between_submissions : float
            Seconds to wait between submissions (rate limiting)
        max_retries : int
            Maximum retry attempts per DOI
            
        Returns
        -------
        Dict[str, Any]
            Detailed results of batch processing
        """
        csv_path = Path(csv_file)
        if not csv_path.exists():
            return {
                'success': False,
                'error': f"CSV file not found: {csv_file}",
                'results': []
            }
        
        print("🚀 Starting batch DOI registration...")
        print(f"   CSV file: {csv_path}")
        print(f"   Environment: {'SANDBOX' if use_sandbox else 'PRODUCTION'}")
        print(f"   Delay between submissions: {delay_between_submissions}s")
        
        # Use appropriate credentials
        submit_username = self.sandbox_username if use_sandbox else self.username
        submit_password = self.sandbox_password if use_sandbox else self.password
        
        # Check for conflicts if requested
        conflict_results = None
        if check_conflicts:
            member_id = os.getenv("CROSSREF_MEMBER_ID")
            if member_id:
                conflict_results = self.check_doi_conflicts(csv_file, member_id)
                if conflict_results.get('conflicts'):
                    response = input(f"\n⚠️  Found {len(conflict_results['conflicts'])} DOI conflicts. Continue anyway? (y/N): ")
                    if response.lower() != 'y':
                        return {
                            'success': False,
                            'error': "Registration cancelled due to DOI conflicts",
                            'conflict_check': conflict_results,
                            'results': []
                        }
        
        # Process CSV with in-memory XML generation (using generator - no file creation!)
        print("\n📡 Processing CSV and submitting DOIs to Crossref...")
        
        try:
            # Use generator to process XML in memory - no temporary files!
            xml_generator = self.csv_converter.generate_xml_from_csv(csv_file)
            
        except Exception as e:
            return {
                'success': False,
                'error': f"CSV processing failed: {e}",
                'conflict_check': conflict_results,
                'results': []
            }
        
        # Submit each XML directly from memory using the generator
        submission_results = []
        successful = 0
        failed = 0
        
        for i, (xml_content, metadata) in enumerate(xml_generator, 1):
            doi = metadata['doi']
            title = metadata.get('title', '(no title)')
            
            # Progress reporting every 100 entries
            if i % 100 == 0:
                print(f"\n📈 {i} entries processed so far...")
            
            print(f"\n   [{i}] Processing: {doi}")
            print(f"      Title: {title}")
            
            # Attempt submission with retries
            success = False
            attempts = 0
            last_error = None
            
            while attempts < max_retries and not success:
                attempts += 1
                
                try:
                    print(f"      Attempt {attempts}/{max_retries}...")
                    success = deposit_xml_content(
                        submit_username, 
                        submit_password, 
                        xml_content,
                        doi,
                        use_sandbox=use_sandbox
                    )
                    
                    if success:
                        print("      ✅ Submission successful!")
                        successful += 1
                        break
                    else:
                        last_error = "Submission failed (unknown reason)"
                        
                except Exception as e:
                    last_error = str(e)
                    print(f"      ❌ Attempt {attempts} failed: {e}")
                
                # Wait before retry (except on last attempt)
                if attempts < max_retries and not success:
                    print(f"      ⏳ Waiting {delay_between_submissions}s before retry...")
                    time.sleep(delay_between_submissions)
            
            # Record result
            result_entry = {
                'doi': doi,
                'title': title,
                'success': success,
                'attempts': attempts,
                'error': None if success else last_error,
                'batch_id': metadata.get('batch_id'),
                'row_number': metadata.get('row_number')
            }
            submission_results.append(result_entry)
            
            if not success:
                failed += 1
                print(f"      ❌ Final result: FAILED after {attempts} attempts")
            
            # Rate limiting delay between submissions (except for the last one)
            print(f"      ⏳ Waiting {delay_between_submissions}s before next submission...")
            time.sleep(delay_between_submissions)
        
        # Summary
        total_processed = len(submission_results)
        print(f"\n📊 Batch Processing Summary:")
        print(f"   Total DOIs processed: {total_processed}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        if total_processed > 0:
            print(f"   Success rate: {(successful/total_processed*100):.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed submissions:")
            for result in submission_results:
                if not result['success']:
                    print(f"   - {result['doi']}: {result['error']}")
        
        return {
            'success': failed == 0,
            'total_dois': total_processed,
            'successful_submissions': successful,
            'failed_submissions': failed,
            'success_rate': successful/total_processed if total_processed else 0,
            'conflict_check': conflict_results,
            'results': submission_results,
            'environment': 'sandbox' if use_sandbox else 'production'
        }
    
    def verify_submissions(self, batch_results: Dict[str, Any], 
                          member_id: str) -> Dict[str, Any]:
        """
        Verify that submitted DOIs appear in Crossref system.
        
        Parameters
        ----------
        batch_results : Dict[str, Any]
            Results from register_batch()
        member_id : str
            Crossref member ID
            
        Returns
        -------
        Dict[str, Any]
            Verification results
        """
        if batch_results['environment'] == 'sandbox':
            print("⚠️  Skipping verification - sandbox DOIs are not in production system")
            return {'skipped': True, 'reason': 'sandbox environment'}
        
        print("🔍 Verifying submitted DOIs...")
        
        # Get successful DOIs from batch results
        submitted_dois = [
            result['doi'] for result in batch_results['results'] 
            if result['success']
        ]
        
        if not submitted_dois:
            return {'verified': [], 'missing': [], 'total_submitted': 0}
        
        print(f"   Checking {len(submitted_dois)} submitted DOIs...")
        
        # Wait a moment for Crossref to process
        print("   ⏳ Waiting 30 seconds for Crossref processing...")
        time.sleep(30)
        
        # Get current DOIs from Crossref
        try:
            current_dois = list_existing_dois(int(member_id), rows=2000)
            current_set = set(current_dois)
            
            verified = [doi for doi in submitted_dois if doi in current_set]
            missing = [doi for doi in submitted_dois if doi not in current_set]
            
            print(f"   ✅ Verified: {len(verified)}/{len(submitted_dois)} DOIs")
            
            if missing:
                print(f"   ⚠️  Missing DOIs (may need more processing time):")
                for doi in missing[:5]:
                    print(f"      - {doi}")
            
            return {
                'verified': verified,
                'missing': missing,
                'total_submitted': len(submitted_dois),
                'verification_rate': len(verified)/len(submitted_dois) if submitted_dois else 0
            }
            
        except Exception as e:
            print(f"   ❌ Verification failed: {e}")
            return {
                'error': str(e),
                'total_submitted': len(submitted_dois)
            }


def main():
    """Main function for command-line usage."""
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Register DOIs from CSV file using Crossref API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('csv_file', help='Input CSV file with publication data')
    parser.add_argument('--sandbox', action='store_true', 
                       help='Use sandbox environment (default: True for safety)')
    parser.add_argument('--production', action='store_true',
                       help='Use PRODUCTION environment (CAUTION: registers real DOIs!)')
    parser.add_argument('--no-conflict-check', action='store_true',
                       help='Skip checking for existing DOI conflicts')
    parser.add_argument('--delay', type=float, default=3.0,
                       help='Delay between submissions in seconds (default: 3.0)')
    parser.add_argument('--retries', type=int, default=3,
                       help='Maximum retry attempts per DOI (default: 3)')
    parser.add_argument('--verify', action='store_true',
                       help='Verify submissions by checking Crossref API after processing')
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
    member_id = os.getenv("CROSSREF_MEMBER_ID")
    
    if not username or not password or not member_id:
        print("❌ Error: Missing credentials!")
        print("Please ensure your .env file contains:")
        print("  CROSSREF_USERNAME=your_username")
        print("  CROSSREF_PASSWORD=your_password")
        print("  CROSSREF_MEMBER_ID=your_member_id")
        return 1
    
    # Determine environment
    use_sandbox = not args.production  # Default to sandbox unless --production specified
    
    if args.production:
        response = input("⚠️  WARNING: You are about to register DOIs in PRODUCTION! Continue? (type 'YES' to confirm): ")
        if response != 'YES':
            print("Registration cancelled.")
            return 0
        use_sandbox = False
    elif not use_sandbox:
        print("Using sandbox environment for safe testing")
    
    # Create registration handler
    registrar = BatchDOIRegistration(
        username=username,
        password=password,
        sandbox_username=sandbox_username,
        sandbox_password=sandbox_password,
        depositor_name=args.depositor_name,
        depositor_email=args.depositor_email
    )
    
    # Process batch registration
    results = registrar.register_batch(
        csv_file=args.csv_file,
        use_sandbox=use_sandbox,
        check_conflicts=not args.no_conflict_check,
        delay_between_submissions=args.delay,
        max_retries=args.retries
    )
    
    # Verify submissions if requested
    if args.verify and results['success'] and results['successful_submissions'] > 0:
        verification = registrar.verify_submissions(results, member_id)
        results['verification'] = verification
    
    # Final summary
    if results['success']:
        print(f"\n🎉 Batch registration completed successfully!")
        env_label = "sandbox" if use_sandbox else "production"
        print(f"   Environment: {env_label}")
        print(f"   Processed: {results['successful_submissions']}/{results['total_dois']} DOIs")
        
        if 'verification' in results and not results['verification'].get('skipped'):
            ver = results['verification']
            print(f"   Verified: {len(ver.get('verified', []))}/{ver.get('total_submitted', 0)} DOIs")
    else:
        print(f"\n❌ Batch registration failed!")
        if 'error' in results:
            print(f"   Error: {results['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())