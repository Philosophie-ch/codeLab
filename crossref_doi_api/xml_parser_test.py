from pathlib import Path
import requests
from typing import Dict, Any, Optional, Union, List
from dotenv import load_dotenv

JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]
JSONArray = List[JSONValue]
JSONType = Union[JSONObject, JSONArray, str, int, float, bool, None]


def validate_xml_with_crossref_parser(xml_file: Union[str, Path]) -> Dict[str, Any]:
    """
    Validate XML file using Crossref's online XML parser.

    Parameters
    ----------
    xml_file : str or Path
        Path to the XML file to validate.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing validation results with keys:
        - 'success': bool indicating if validation passed
        - 'status_code': int HTTP response code
        - 'response_text': str raw response from parser
        - 'errors': List[str] extracted error messages
        - 'warnings': List[str] extracted warning messages
    """
    parser_url = "https://www.crossref.org/02publishers/parser.html"
    
    print(f"   Validating file: {xml_file}")
    
    result: Dict[str, Any] = {
        'success': False,
        'status_code': 0,
        'response_text': '',
        'errors': [],
        'warnings': []
    }
    
    try:
        if not Path(xml_file).exists():
            result['errors'].append(f"File not found: {xml_file}")
            return result
            
        with open(xml_file, 'rb') as f:
            files = {'file': (Path(xml_file).name, f, 'application/xml')}
            
            # The parser endpoint might be different, let's try the common form submission
            response = requests.post(parser_url, files=files, timeout=30)
            
            result['status_code'] = response.status_code
            result['response_text'] = response.text
            
            if response.status_code == 200:
                result['success'] = True
                print("✅ XML parser request successful")
                
                # Parse the HTML response for validation results
                response_text = response.text.lower()
                
                if 'error' in response_text:
                    # Try to extract error messages from HTML
                    lines = response.text.split('\n')
                    errors_list = result['errors']
                    if isinstance(errors_list, list):
                        for line in lines:
                            if 'error' in line.lower() and '<' in line:
                                errors_list.append(line.strip())
                
                if 'warning' in response_text:
                    # Try to extract warning messages
                    lines = response.text.split('\n')
                    warnings_list = result['warnings']
                    if isinstance(warnings_list, list):
                        for line in lines:
                            if 'warning' in line.lower() and '<' in line:
                                warnings_list.append(line.strip())
                            
                if 'valid' in response_text or 'success' in response_text:
                    print("✅ XML appears to be valid")
                else:
                    errors_list = result['errors']
                    if isinstance(errors_list, list) and errors_list:
                        print(f"❌ Found {len(errors_list)} errors in XML")
                        result['success'] = False
                    else:
                        print("⚠️  Parser response unclear - check response_text")
                    
            else:
                print(f"❌ Parser request failed with status: {response.status_code}")
                errors_list = result['errors']
                if isinstance(errors_list, list):
                    errors_list.append(f"HTTP {response.status_code}: {response.reason}")
                
    except FileNotFoundError:
        error_msg = f"File not found: {xml_file}"
        errors_list = result['errors']
        if isinstance(errors_list, list):
            errors_list.append(error_msg)
        print(f"❌ {error_msg}")
    except requests.RequestException as e:
        error_msg = f"Network error: {e}"
        errors_list = result['errors']
        if isinstance(errors_list, list):
            errors_list.append(error_msg)
        print(f"❌ {error_msg}")
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        errors_list = result['errors']
        if isinstance(errors_list, list):
            errors_list.append(error_msg)
        print(f"❌ {error_msg}")
        
    return result


def validate_xml_locally(xml_file: Union[str, Path]) -> Dict[str, Any]:
    """
    Perform local XML validation checks.

    Parameters
    ----------
    xml_file : str or Path
        Path to the XML file to validate.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing local validation results.
    """
    result: Dict[str, Any] = {
        'success': False,
        'file_exists': False,
        'file_size': 0,
        'is_xml': False,
        'has_doi_batch': False,
        'has_doi_data': False,
        'errors': []
    }
    
    try:
        xml_path = Path(xml_file)
        
        # Check file existence
        if not xml_path.exists():
            errors_list = result['errors']
            if isinstance(errors_list, list):
                errors_list.append("File does not exist")
            return result
        result['file_exists'] = True
        
        # Check file size
        result['file_size'] = xml_path.stat().st_size
        if result['file_size'] == 0:
            errors_list = result['errors']
            if isinstance(errors_list, list):
                errors_list.append("File is empty")
            return result
        
        # Read and check content
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Basic XML checks
        errors_list = result['errors']
        if not isinstance(errors_list, list):
            errors_list = []
            result['errors'] = errors_list
            
        if content.strip().startswith('<?xml'):
            result['is_xml'] = True
        else:
            errors_list.append("File does not start with XML declaration")
            
        # Crossref-specific checks
        if '<doi_batch' in content:
            result['has_doi_batch'] = True
        else:
            errors_list.append("Missing doi_batch element")
            
        if '<doi_data>' in content or '<doi>' in content:
            result['has_doi_data'] = True
        else:
            errors_list.append("Missing DOI data elements")
            
        # Success if no errors
        if not errors_list:
            result['success'] = True
            print("✅ Local validation passed")
        else:
            print(f"❌ Local validation failed: {len(errors_list)} errors")
            
    except UnicodeDecodeError:
        errors_list = result['errors']
        if isinstance(errors_list, list):
            errors_list.append("File encoding error - not valid UTF-8")
    except Exception as e:
        errors_list = result['errors']
        if isinstance(errors_list, list):
            errors_list.append(f"Unexpected error: {e}")
        
    return result


def generate_test_report(xml_file: Union[str, Path], 
                        local_result: Dict[str, Any], 
                        parser_result: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a comprehensive test report.

    Parameters
    ----------
    xml_file : str or Path
        The XML file that was tested.
    local_result : Dict[str, Any]
        Results from local validation.
    parser_result : Dict[str, Any], optional
        Results from Crossref parser validation.

    Returns
    -------
    str
        Formatted test report.
    """
    report = []
    report.append("="*60)
    report.append(f"XML VALIDATION REPORT: {Path(xml_file).name}")
    report.append("="*60)
    
    # Local validation section
    report.append("\n📁 LOCAL VALIDATION:")
    report.append(f"   File exists: {'✅' if local_result['file_exists'] else '❌'}")
    report.append(f"   File size: {local_result['file_size']} bytes")
    report.append(f"   Valid XML format: {'✅' if local_result['is_xml'] else '❌'}")
    report.append(f"   Has doi_batch: {'✅' if local_result['has_doi_batch'] else '❌'}")
    report.append(f"   Has DOI data: {'✅' if local_result['has_doi_data'] else '❌'}")
    report.append(f"   Overall: {'✅ PASS' if local_result['success'] else '❌ FAIL'}")
    
    if local_result['errors']:
        report.append("\n   Local Errors:")
        for error in local_result['errors']:
            report.append(f"   - {error}")
    
    # Parser validation section
    if parser_result:
        report.append("\n🌐 CROSSREF PARSER VALIDATION:")
        report.append(f"   HTTP Status: {parser_result['status_code']}")
        report.append(f"   Parser Success: {'✅' if parser_result['success'] else '❌'}")
        
        if parser_result['errors']:
            report.append("\n   Parser Errors:")
            for error in parser_result['errors'][:5]:  # Limit to first 5
                report.append(f"   - {error}")
                
        if parser_result['warnings']:
            report.append("\n   Parser Warnings:")
            for warning in parser_result['warnings'][:5]:  # Limit to first 5
                report.append(f"   - {warning}")
    
    # Overall result
    report.append("\n" + "="*60)
    local_ok = local_result['success']
    parser_ok = parser_result['success'] if parser_result else True
    
    if local_ok and parser_ok:
        report.append("🎉 OVERALL RESULT: XML IS READY FOR SUBMISSION")
    elif local_ok:
        report.append("⚠️  OVERALL RESULT: LOCAL VALIDATION PASSED, CHECK PARSER RESULTS")
    else:
        report.append("❌ OVERALL RESULT: FIX LOCAL ISSUES BEFORE SUBMISSION")
    
    report.append("="*60)
    
    return "\n".join(report)


if __name__ == "__main__":
    load_dotenv()
    
    import sys
    
    if len(sys.argv) > 1:
        xml_file = Path(sys.argv[1])
    else:
        xml_file = Path("test_doi.xml")
    
    print("🔍 Starting XML validation tests...")
    print(f"   Target file: {xml_file}")
    
    # Step 1: Local validation
    print("\n1. Running local validation...")
    local_result = validate_xml_locally(xml_file)
    
    # Step 2: Crossref parser validation
    print("\n2. Testing with Crossref XML parser...")
    parser_result = None
    
    if local_result['file_exists']:
        parser_result = validate_xml_with_crossref_parser(xml_file)
    else:
        print("   Skipping parser test - file does not exist")
    
    # Step 3: Generate report
    print("\n3. Generating test report...")
    report = generate_test_report(xml_file, local_result, parser_result)
    print(report)