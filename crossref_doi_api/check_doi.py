#!/usr/bin/env python3
"""
DOI Metadata Checker

Check the metadata and status of registered DOIs using various methods.
"""

import requests
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
from dotenv import load_dotenv
import os
from api_test import list_existing_dois

def check_doi_resolution(doi: str) -> Dict[str, Any]:
    """Check if DOI resolves correctly."""
    print(f"🔗 Testing DOI resolution for: {doi}")
    
    try:
        response = requests.head(f"https://doi.org/{doi}", allow_redirects=True, timeout=10)
        if response.status_code == 200:
            final_url = response.url
            print(f"   ✅ DOI resolves to: {final_url}")
            return {"success": True, "resolves_to": final_url, "status": response.status_code}
        else:
            print(f"   ❌ DOI resolution failed: HTTP {response.status_code}")
            return {"success": False, "status": response.status_code}
    except requests.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        return {"success": False, "error": str(e)}

def get_crossref_metadata(doi: str) -> Dict[str, Any]:
    """Get metadata from Crossref public API."""
    print(f"🔍 Fetching Crossref metadata for: {doi}")
    
    try:
        response = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"Accept": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            work = data.get("message", {})
            
            print(f"   ✅ Found in Crossref API!")
            print(f"   📖 Title: {work.get('title', ['Unknown'])[0]}")
            authors = ', '.join([f"{a.get('given', '')} {a.get('family', '')}" for a in work.get('author', [])])
            print(f"   👤 Authors: {authors}")
            print(f"   📅 Published: {work.get('published-print', {}).get('date-parts', [[]])[0]}")
            print(f"   🏢 Publisher: {work.get('publisher', 'Unknown')}")
            
            return {"success": True, "metadata": work}
        elif response.status_code == 404:
            print(f"   ⏳ Not yet indexed in public API (this is normal for new DOIs)")
            return {"success": False, "reason": "not_yet_indexed"}
        else:
            print(f"   ❌ API error: HTTP {response.status_code}")
            return {"success": False, "status": response.status_code}
            
    except requests.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        return {"success": False, "error": str(e)}

def get_content_negotiation_metadata(doi: str) -> Dict[str, Any]:
    """Get metadata using content negotiation."""
    print(f"📄 Testing content negotiation for: {doi}")
    
    formats = {
        "CSL JSON": "application/vnd.citationstyles.csl+json",
        "BibTeX": "application/x-bibtex",
        "RIS": "application/x-research-info-systems"
    }
    
    results = {}
    
    for format_name, mime_type in formats.items():
        try:
            response = requests.get(
                f"https://doi.org/{doi}",
                headers={"Accept": mime_type},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"   ✅ {format_name}: Available")
                results[format_name.lower().replace(" ", "_")] = {
                    "success": True,
                    "content": response.text[:500] + "..." if len(response.text) > 500 else response.text
                }
            else:
                print(f"   ⚠️  {format_name}: HTTP {response.status_code}")
                results[format_name.lower().replace(" ", "_")] = {
                    "success": False,
                    "status": response.status_code
                }
        except requests.RequestException as e:
            print(f"   ❌ {format_name}: {e}")
            results[format_name.lower().replace(" ", "_")] = {
                "success": False,
                "error": str(e)
            }
    
    return results

def check_in_member_account(doi: str) -> Dict[str, Any]:
    """Check if DOI appears in your member account."""
    print(f"🏢 Checking member account for: {doi}")
    
    load_dotenv()
    member_id = os.getenv("CROSSREF_MEMBER_ID")
    
    if not member_id:
        print("   ❌ No CROSSREF_MEMBER_ID found in .env")
        return {"success": False, "error": "missing_member_id"}
    
    try:
        dois = list_existing_dois(int(member_id), rows=100)
        
        if doi in dois:
            print(f"   ✅ Found in your member account!")
            # Find position in list (most recent first)
            position = dois.index(doi) + 1
            print(f"   📍 Position: #{position} in recent DOIs")
            return {"success": True, "found": True, "position": position}
        else:
            print(f"   ⏳ Not yet visible in member account")
            # Show recent DOIs for context
            print(f"   📋 Recent DOIs in account:")
            for i, recent_doi in enumerate(dois[:5], 1):
                print(f"      {i}. {recent_doi}")
            return {"success": True, "found": False, "recent_dois": dois[:5]}
            
    except Exception as e:
        print(f"   ❌ Error checking member account: {e}")
        return {"success": False, "error": str(e)}

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_doi.py <DOI>")
        print("Example: python check_doi.py 10.48106/dial.v8.i32.06")
        sys.exit(1)
    
    doi = sys.argv[1].strip()
    print(f"🔎 Comprehensive DOI Check: {doi}")
    print("=" * 60)
    
    # Run all checks
    resolution = check_doi_resolution(doi)
    print()
    
    crossref_meta = get_crossref_metadata(doi)
    print()
    
    content_neg = get_content_negotiation_metadata(doi)
    print()
    
    member_check = check_in_member_account(doi)
    print()
    
    # Summary
    print("📊 SUMMARY:")
    print(f"   DOI Resolution: {'✅' if resolution['success'] else '❌'}")
    print(f"   Crossref API: {'✅' if crossref_meta['success'] else '⏳'}")
    print(f"   Content Negotiation: {'✅' if any(r['success'] for r in content_neg.values()) else '❌'}")
    print(f"   Member Account: {'✅' if member_check.get('found') else '⏳'}")
    
    if resolution['success']:
        print(f"\n🎉 DOI is ACTIVE and working!")
        print(f"   Link: https://doi.org/{doi}")
    else:
        print(f"\n⚠️  DOI may need more time to become fully active.")

if __name__ == "__main__":
    main()