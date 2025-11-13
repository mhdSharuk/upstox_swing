"""
Pre-Deployment Setup Verification Script
Run this before deploying to PythonAnywhere to check your configuration
"""

import os
import sys
import json

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(message):
    """Print a section header"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{message}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


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


def print_info(message):
    """Print an info message"""
    print(f"  {message}")


def check_flask_installation():
    """Check if Flask is installed"""
    try:
        import flask
        print_check(f"Flask installed (version {flask.__version__})", True)
        return True
    except ImportError:
        print_check("Flask NOT installed", False)
        print_info("Install with: pip install Flask")
        return False


def check_credentials_file():
    """Check if credentials are properly configured"""
    all_good = True
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import credentials
        
        # Check Upstox credentials
        checks = [
            ('UPSTOX_API_KEY', credentials.UPSTOX_API_KEY, 'your_api_key_here'),
            ('UPSTOX_API_SECRET', credentials.UPSTOX_API_SECRET, 'your_api_secret_here'),
            ('UPSTOX_CLIENT_ID', credentials.UPSTOX_CLIENT_ID, 'your_api_key_here'),
            ('UPSTOX_TOTP_SECRET', credentials.UPSTOX_TOTP_SECRET, 'your_totp_secret_here'),
        ]
        
        for name, value, placeholder in checks:
            if value == placeholder:
                print_check(f"{name} NOT configured (still has placeholder)", False)
                all_good = False
            else:
                print_check(f"{name} configured", True)
        
        # Check Flask secret key
        if credentials.FLASK_SECRET_KEY == "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY":
            print_check("FLASK_SECRET_KEY NOT configured (still placeholder)", False)
            print_warning("Generate a secure key with:")
            print_info('python -c "import secrets; print(secrets.token_urlsafe(32))"')
            all_good = False
        elif len(credentials.FLASK_SECRET_KEY) < 20:
            print_check("FLASK_SECRET_KEY is too short (less than 20 chars)", False)
            all_good = False
        else:
            print_check("FLASK_SECRET_KEY configured", True)
        
        # Check webhook URL
        if hasattr(credentials, 'WEBHOOK_URL'):
            if 'mhdsharuk.pythonanywhere.com' in credentials.WEBHOOK_URL:
                print_check(f"WEBHOOK_URL configured: {credentials.WEBHOOK_URL}", True)
            else:
                print_check("WEBHOOK_URL configured but may be incorrect", False)
                print_info(f"Expected: https://mhdsharuk.pythonanywhere.com/upstox-webhook")
                print_info(f"Got: {credentials.WEBHOOK_URL}")
                all_good = False
        else:
            print_check("WEBHOOK_URL NOT found in credentials", False)
            print_info("Add: WEBHOOK_URL = 'https://mhdsharuk.pythonanywhere.com/upstox-webhook'")
            all_good = False
        
        # Check Google credentials
        if credentials.GOOGLE_SHEET_ID == "your_google_sheet_id_here":
            print_check("GOOGLE_SHEET_ID NOT configured", False)
            all_good = False
        else:
            print_check("GOOGLE_SHEET_ID configured", True)
        
        return all_good
        
    except ImportError:
        print_check("config/credentials.py file NOT found", False)
        print_info("Create config/credentials.py from the template")
        return False
    except AttributeError as e:
        print_check(f"Missing credential field: {e}", False)
        return False


def check_service_account_file():
    """Check if service account JSON file exists and is valid"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import credentials
        sa_file = credentials.SERVICE_ACCOUNT_FILE
    except:
        sa_file = "service_account.json"
    
    if not os.path.exists(sa_file):
        print_check(f"Service account file '{sa_file}' NOT found", False)
        print_info("Download from Google Cloud Console and place in project root")
        return False
    
    try:
        with open(sa_file, 'r') as f:
            data = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            print_check(f"Service account file missing fields: {missing}", False)
            return False
        
        print_check(f"Service account file is valid", True)
        print_info(f"Email: {data.get('client_email')}")
        print_warning(f"Remember to share your Google Sheet with this email!")
        return True
        
    except json.JSONDecodeError:
        print_check(f"Service account file is not valid JSON", False)
        return False


def check_flask_app_file():
    """Check if flask_app.py exists"""
    if os.path.exists('flask_app.py'):
        print_check("flask_app.py exists", True)
        return True
    else:
        print_check("flask_app.py NOT found", False)
        print_info("Copy flask_app.py from the outputs folder")
        return False


def check_project_structure():
    """Check if all required directories and files exist"""
    all_good = True
    
    required_items = [
        ('config/', True),
        ('auth/', True),
        ('data_fetcher/', True),
        ('indicators/', True),
        ('storage/', True),
        ('utils/', True),
        ('main.py', False),
        ('requirements.txt', False),
    ]
    
    for item, is_dir in required_items:
        if is_dir:
            exists = os.path.isdir(item)
            item_type = "directory"
        else:
            exists = os.path.isfile(item)
            item_type = "file"
        
        if exists:
            print_check(f"{item_type.capitalize()} '{item}' exists", True)
        else:
            print_check(f"{item_type.capitalize()} '{item}' NOT found", False)
            all_good = False
    
    return all_good


def generate_cron_urls():
    """Generate the URLs needed for cron-job.org"""
    try:
        from config import credentials
        secret = credentials.FLASK_SECRET_KEY
        base_url = "https://mhdsharuk.pythonanywhere.com"
        
        print_header("URLs for cron-job.org")
        
        print(f"{YELLOW}Token Request URL:{RESET}")
        print(f"  {base_url}/request-token?secret={secret}")
        
        print(f"\n{YELLOW}Run Job URL:{RESET}")
        print(f"  {base_url}/run-job?secret={secret}")
        
        print(f"\n{YELLOW}Token Status URL:{RESET}")
        print(f"  {base_url}/token-status?secret={secret}")
        
        print(f"\n{YELLOW}Webhook URL (for Upstox app config):{RESET}")
        print(f"  {base_url}/upstox-webhook")
        
        print(f"\n{YELLOW}Schedule for cron-job.org:{RESET}")
        print("  Token Request:  8:00 AM IST (2:30 AM UTC) - Daily")
        print("  Token Retry 1:  8:30 AM IST (3:00 AM UTC) - Daily")
        print("  Token Retry 2:  9:00 AM IST (3:30 AM UTC) - Daily")
        print("  Data Fetch 1:   9:15 AM IST (3:45 AM UTC) - Daily")
        print("  Data Fetch 2:  11:20 AM IST (5:50 AM UTC) - Daily")
        print("  Data Fetch 3:   1:25 PM IST (7:55 AM UTC) - Daily")
        print("  Data Fetch 4:   3:30 PM IST (10:00 AM UTC) - Daily")
        
    except Exception as e:
        print_warning(f"Could not generate URLs: {e}")


def main():
    """Run all checks"""
    print(f"\n{GREEN}{'=' * 60}{RESET}")
    print(f"{GREEN}PRE-DEPLOYMENT VERIFICATION - PYTHONANYWHERE + CRON-JOB.ORG{RESET}")
    print(f"{GREEN}{'=' * 60}{RESET}")
    
    all_passed = True
    
    # Check project structure
    print_header("1. Checking Project Structure")
    all_passed &= check_project_structure()
    
    # Check Flask app
    print_header("2. Checking Flask Application")
    all_passed &= check_flask_app_file()
    all_passed &= check_flask_installation()
    
    # Check credentials
    print_header("3. Checking Credentials Configuration")
    all_passed &= check_credentials_file()
    
    # Check service account
    print_header("4. Checking Google Service Account")
    all_passed &= check_service_account_file()
    
    # Generate URLs
    generate_cron_urls()
    
    # Final summary
    print_header("VERIFICATION SUMMARY")
    
    if all_passed:
        print(f"{GREEN}✓ All checks passed! Ready for deployment.{RESET}\n")
        print(f"Next steps:")
        print(f"  1. Upload files to PythonAnywhere")
        print(f"  2. Configure Flask web app on PythonAnywhere")
        print(f"  3. Setup cron jobs on cron-job.org")
        print(f"  4. Configure webhook URL in Upstox app")
        print(f"\n{BLUE}See DEPLOYMENT_GUIDE.md for detailed instructions{RESET}")
    else:
        print(f"{RED}✗ Some checks failed. Please fix the issues above.{RESET}\n")
        print("Common fixes:")
        print("  1. Run: pip install Flask")
        print("  2. Configure config/credentials.py")
        print("  3. Add service_account.json to project root")
        print("  4. Copy flask_app.py from outputs folder")
    
    print(f"\n{BLUE}{'=' * 60}{RESET}\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())