from pathlib import Path
import requests
from typing import Any, Dict, List, Union
import os
from dotenv import load_dotenv

# Clean JSON typing approach
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]
JSONArray = List[JSONValue]
JSONType = Union[JSONObject, JSONArray, str, int, float, bool, None]


def get_crossref_member(member_id: str) -> JSONType:
    """
    Fetch DOI prefixes for a given Crossref member ID.

    Parameters
    ----------
    member_id : str or int
        Your Crossref member ID.

    Returns
    -------
    list of str
        A list of DOI prefixes assigned to the member.
    """
    url = f"https://api.crossref.org/members/{member_id}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching data from Crossref API: {e}")
        return {}
    
    data: JSONType = response.json()
    return data


def get_crossref_prefixes(cr_json: JSONType) -> List[str]:
    """
    Extract DOI prefixes from Crossref member JSON response.

    Parameters
    ----------
    cr_json : JSONType
        The JSON response from get_crossref_member.

    Returns
    -------
    list of str
        A list of DOI prefixes assigned to the member.
    """

    if not isinstance(cr_json, dict):
        raise ValueError(f"Expected JSON object, got {type(cr_json).__name__}")
    
    message = cr_json.get("message")
    if not isinstance(message, dict):
        return []
    
    prefixes = message.get("prefixes", [])
    if not isinstance(prefixes, list):
        return []
    
    return [str(prefix) for prefix in prefixes if isinstance(prefix, str)]

    return prefixes



def list_existing_dois(member_id: int, rows: int) -> List[str]:
    """
    List DOIs already registered under your Crossref member account.

    Parameters
    ----------
    member_id : int
        Your Crossref member ID.
    rows : int, optional
        Number of results to fetch (default 20).

    Returns
    -------
    List[str]
        A list of DOI strings.
    """
    url = f"https://api.crossref.org/members/{member_id}/works"
    params = {"rows": rows}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching DOIs: {e}")
        return []

    data: Dict[str, Any] = response.json()
    items = data.get("message", {}).get("items", [])

    dois = [item.get("DOI", "") for item in items if "DOI" in item]

    #print(f"Found {len(dois)} DOIs:")
    #for doi in dois:
        #print(doi)

    return dois


def test_crossref_auth(username: str, password: str) -> bool:
    """
    Test Crossref authentication by fetching the deposit submission log.

    Parameters
    ----------
    username : str
        Your Crossref login username (often your email or email/role).
    password : str
        Your Crossref password.

    Returns
    -------
    bool
        True if authentication succeeds, False otherwise.
    """
    # This endpoint returns an HTML page of your submission history
    url = "https://doi.crossref.org/servlet/submissionDownload"

    data = {
        "login_id": username,
        "login_passwd": password,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error connecting to Crossref: {e}")
        return False

    if response.status_code == 200 and "DOCTYPE html" in response.text:
        print("✅ Authentication successful!")
        return True
    else:
        print(f"❌ Authentication failed! Status: {response.status_code}")
        print(response.text[:200])  # Show start of response for debugging
        return False

def deposit_test_doi(
    username: str,
    password: str,
    xml_file: Union[str, Path],
    use_sandbox: bool = True
) -> bool:
    """
    Deposit a DOI to Crossref using an XML metadata file.

    Parameters
    ----------
    username : str
        Crossref login username (email or email/role).
    password : str
        Crossref login password.
    xml_file : str or Path
        Path to the XML file to upload.
    use_sandbox : bool
        If True, use test server; if False, use production.

    Returns
    -------
    bool
        True if deposit was successful, False otherwise.
    """
    if use_sandbox:
        url = "https://test.crossref.org/servlet/deposit"  # sandbox endpoint
        print("📝 Using SANDBOX environment")
    else:
        url = "https://doi.crossref.org/servlet/deposit"  # production endpoint
        print("⚠️  Using PRODUCTION environment")

    with open(xml_file, "rb") as f:
        files = {"fname": f}
        data = {
            "operation": "doMDUpload",
            "login_id": username,
            "login_passwd": password,
        }
        try:
            r = requests.post(url, data=data, files=files, timeout=30)
            r.raise_for_status()
            print("✅ Deposit submitted successfully!")
            print("Server response:")
            print(r.text)
            return True
        except requests.RequestException as e:
            print(f"❌ Error depositing DOI: {e}")
            if 'r' in locals():
                print(f"Response text: {r.text[:2000]}")
            return False

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    member_id = os.getenv("CROSSREF_MEMBER_ID")
    username = os.getenv("CROSSREF_USERNAME")
    password = os.getenv("CROSSREF_PASSWORD")
    
    if not username or not password or not member_id:
        print("❌ Error: Missing credentials!")
        print("Please create a .env file with:")
        print("  CROSSREF_USERNAME=your_username")
        print("  CROSSREF_PASSWORD=your_password")
        print("  CROSSREF_MEMBER_ID=your_member_id (optional)")
        exit(1)
    
    xml_file = Path("test_doi.xml")
    
    print("="*50)
    print("Crossref DOI Registration Test")
    print("="*50)
    
    # Step 1: Get member information and prefixes
    print("\n1. Fetching member information...")
    member_data = get_crossref_member(member_id)
    if member_data:
        prefixes = get_crossref_prefixes(member_data)
        print(f"   Prefixes available: {prefixes}")
    
    # Step 2: Test authentication
    print("\n2. Testing authentication...")
    auth_success = test_crossref_auth(username, password)
    
    if auth_success:
        # Step 3: List existing DOIs
        print("\n3. Checking existing DOIs...")
        existing_dois = list_existing_dois(int(member_id), rows=5)
        if existing_dois:
            print(f"   Found {len(existing_dois)} existing DOIs:")
            for doi in existing_dois[:3]:  # Show first 3
                print(f"   - {doi}")
        
        # Step 4: Test DOI deposit to sandbox
        print("\n4. Testing DOI deposit to SANDBOX...")
        print(f"   XML file: {xml_file}")
        success = deposit_test_doi(username, password, xml_file, use_sandbox=True)
        
        if success:
            print("\n✅ All tests completed successfully!")
            print("\nNOTE: This was a SANDBOX test. The DOI is not actually registered.")
            print("To register a real DOI, set use_sandbox=False (use with caution!)")
    else:
        print("\n❌ Authentication failed. Please check credentials.")
