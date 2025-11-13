"""
Setup Verification Script
Run this to check if your configuration is correct before running the main pipeline
"""

import sys
import os

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_check(message, status):
    """Print a check result with color"""
    if status:
        print(f"{GREEN}✓{RESET} {message}")
        return True
    else:
        print(f"{RED}✗{RESET} {message}")
        return False

def print_warning(message):
    """Print a warning message"""
    print(f"{YELLOW}⚠{RESET} {message}")

def print_header(message):
    """Print a section header"""
    print(f"\n{YELLOW}{'=' * 20}{RESET}")
    print(f"{YELLOW}{message}{RESET}")
    print(f"{YELLOW}{'=' * 20}{RESET}\n")

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_check(f"Python version {version.major}.{version.minor}.{version.micro}", True)
        return True
    else:
        print_check(f"Python version {version.major}.{version.minor}.{version.micro} (requires 3.8+)", False)
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'requests',
        'aiohttp',
        'pandas',
        'numpy',
        'pyotp',
        'gspread',
        'google.oauth2',
        'ijson'
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            __import__(package.replace('google.oauth2', 'google.oauth2.service_account'))
            print_check(f"Package '{package}' installed", True)
        except ImportError:
            print_check(f"Package '{package}' NOT installed", False)
            all_installed = False
    
    return all_installed

def check_credentials_file():
    """Check if credentials file exists and is configured"""
    try:
        from config import credentials
        
        checks = []
        
        # Check Upstox credentials
        if hasattr(credentials, 'UPSTOX_API_KEY'):
            if credentials.UPSTOX_API_KEY != "your_api_key_here":
                checks.append(print_check("Upstox API Key configured", True))
            else:
                checks.append(print_check("Upstox API Key NOT configured", False))
        else:
            checks.append(print_check("Upstox API Key missing", False))
        
        if hasattr(credentials, 'UPSTOX_API_SECRET'):
            if credentials.UPSTOX_API_SECRET != "your_api_secret_here":
                checks.append(print_check("Upstox API Secret configured", True))
            else:
                checks.append(print_check("Upstox API Secret NOT configured", False))
        else:
            checks.append(print_check("Upstox API Secret missing", False))
        
        if hasattr(credentials, 'UPSTOX_TOTP_SECRET'):
            if credentials.UPSTOX_TOTP_SECRET != "your_totp_secret_here":
                checks.append(print_check("Upstox TOTP Secret configured", True))
            else:
                checks.append(print_check("Upstox TOTP Secret NOT configured", False))
        else:
            checks.append(print_check("Upstox TOTP Secret missing", False))
        
        # Check Google credentials
        if hasattr(credentials, 'GOOGLE_SHEET_ID'):
            if credentials.GOOGLE_SHEET_ID != "your_google_sheet_id_here":
                checks.append(print_check("Google Sheet ID configured", True))
            else:
                checks.append(print_check("Google Sheet ID NOT configured", False))
        else:
            checks.append(print_check("Google Sheet ID missing", False))
        
        return all(checks)
        
    except ImportError:
        print_check("config/credentials.py file NOT found", False)
        return False
    except Exception as e:
        print_check(f"Error reading credentials: {e}", False)
        return False

def check_service_account_file():
    """Check if service account JSON file exists"""
    try:
        from config import credentials
        service_account_file = credentials.SERVICE_ACCOUNT_FILE
    except:
        service_account_file = "service_account.json"
    
    if os.path.exists(service_account_file):
        # Try to load it to check if it's valid JSON
        try:
            import json
            with open(service_account_file, 'r') as f:
                data = json.load(f)
            
            # Check for required fields
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            has_required = all(field in data for field in required_fields)
            
            if has_required:
                print_check(f"Service account file '{service_account_file}' is valid", True)
                print(f"  Service account email: {data.get('client_email')}")
                return True
            else:
                print_check(f"Service account file '{service_account_file}' is missing required fields", False)
                return False
        except json.JSONDecodeError:
            print_check(f"Service account file '{service_account_file}' is not valid JSON", False)
            return False
    else:
        print_check(f"Service account file '{service_account_file}' NOT found", False)
        return False

def check_project_structure():
    """Check if all required directories exist"""
    required_dirs = [
        'config',
        'auth',
        'data_fetcher',
        'indicators',
        'storage',
        'utils'
    ]
    
    all_exist = True
    for directory in required_dirs:
        if os.path.isdir(directory):
            print_check(f"Directory '{directory}' exists", True)
        else:
            print_check(f"Directory '{directory}' NOT found", False)
            all_exist = False
    
    return all_exist

def check_token_file():
    """Check if token file exists (not required, but informative)"""
    if os.path.exists('upstox_token.json'):
        print_warning("Existing Upstox token found (upstox_token.json)")
        print("  Token will be validated before use")
        print("  If expired, authentication flow will run automatically")
    else:
        print_warning("No existing Upstox token found")
        print("  Authentication flow will run on first execution")

def main():
    """Run all checks"""
    print(f"\n{GREEN}{'=' * 20}{RESET}")
    print(f"{GREEN}UPSTOX SUPERTREND PROJECT - SETUP VERIFICATION{RESET}")
    print(f"{GREEN}{'=' * 20}{RESET}")
    
    all_passed = True
    
    # Check Python version
    print_header("Checking Python Environment")
    all_passed &= check_python_version()
    
    # Check project structure
    print_header("Checking Project Structure")
    all_passed &= check_project_structure()
    
    # Check dependencies
    print_header("Checking Dependencies")
    deps_ok = check_dependencies()
    all_passed &= deps_ok
    
    if not deps_ok:
        print(f"\n{YELLOW}To install missing packages, run:{RESET}")
        print("  pip install -r requirements.txt")
    
    # Check credentials
    print_header("Checking Credentials Configuration")
    all_passed &= check_credentials_file()
    
    # Check service account file
    print_header("Checking Google Service Account")
    sa_ok = check_service_account_file()
    all_passed &= sa_ok
    
    if not sa_ok:
        print(f"\n{YELLOW}To set up Google service account:{RESET}")
        print("  1. Create a service account in Google Cloud Console")
        print("  2. Download the JSON key file")
        print("  3. Save it as 'service_account.json' in project root")
        print("  4. Share your Google Sheet with the service account email")
    
    # Check token file (informational)
    print_header("Checking Upstox Token")
    check_token_file()
    
    # Final summary
    print_header("SETUP VERIFICATION SUMMARY")
    
    if all_passed:
        print(f"{GREEN}✓ All checks passed! You're ready to run the pipeline.{RESET}")
        print(f"\nTo start the pipeline, run:")
        print(f"  {GREEN}python main.py{RESET}")
    else:
        print(f"{RED}✗ Some checks failed. Please fix the issues above.{RESET}")
        print(f"\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure credentials in config/credentials.py")
        print("  3. Add service_account.json to project root")
    
    print(f"\n{YELLOW}{'=' * 20}{RESET}\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
