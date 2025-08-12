from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
from typing import Any, Dict, List, Union
from pprint import pprint

JSONTypeAtom = Union[str, int, float, bool, None, "JSONType"]
JSONType = Dict[str, JSONTypeAtom]  | List["JSONType"]


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
        return []
    
    data: JSONType = response.json()
    return data


def get_crossref_prefixes(cr_json: JSONType) -> List[str]:
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

    data = cr_json

    if isinstance(data, dict):
        prefixes: List[str] = data.get("message", {}).get("prefixes", [])
    else:
        raise ValueError(f"Unexpected data format: {type(data)}. Expected a dictionary, found\n\n{data}\n\n")

    if prefixes:
        print(f"DOI prefixes for member {member_id}: {prefixes}")
    else:
        print(f"No prefixes found for member {member_id}")

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
    xml_file: Union[str, Path]
) -> None:
    """
    Deposit a DOI to the Crossref sandbox using an XML metadata file.

    Parameters
    ----------
    username : str
        Crossref login username (email or email/role).
    password : str
        Crossref login password.
    xml_file : str or Path
        Path to the XML file to upload.
    """
    url = "https://test.crossref.org/servlet/deposit"  # sandbox endpoint

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
        except requests.RequestException as e:
            print(f"Error depositing DOI: {e}")
            print(f"Section of response: {r.text[:2000]}")
            return

        print("Server response:")
        print(r.text)

if __name__ == "__main__":
    member_id: str = "27938"
    #data = get_crossref_member(member_id)

    #pprint(data)

    #prefixes = get_crossref_prefixes(data)
    #pprint(prefixes)

    #dois = list_existing_dois(member_id, rows=50)
    #pprint(dois)

    # Test authentication
    username = "philipp.blum@philosophie.ch/vere"
    password = "gottlob0dimitri"
    #test_crossref_auth(username, password)

    # Test depositing a DOI
    xml_file = Path("test_doi.xml")
    deposit_test_doi(username, password, xml_file)
