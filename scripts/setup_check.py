"""
Comprehensive Verification Script
Checks both local setup and deployment readiness
Run before first use OR before deploying to PythonAnywhere
"""

import sys
import os
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


# ============================================================================
# SECTION 1: PYTHON ENVIRONMENT
# ============================================================================

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
        ('requests', 'Core HTTP library'),
        ('aiohttp', 'Async HTTP for data fetching'),
        ('pandas', 'Data processing'),
        ('numpy', 'Numerical operations'),
        ('pyotp', 'TOTP authentication'),
        ('gspread', 'Google Sheets API'),
        ('google.oauth2', 'Google authentication'),
        ('ijson', 'JSON streaming'),
        ('Flask', 'Web framework (deployment only)'),
    ]
    
    all_installed = True
    optional_missing = []
    
    for package, description in required_packages:
        try:
            if package == 'Flask':
                # Flask is optional for local use, required for deployment
                try:
                    import flask
                    print_check(f"Package '{package}' installed - {description}", True)
                except ImportError:
                    print_warning(f"Package '{package}' NOT installed - {description}")
                    print_info("Required for deployment, optional for local use")
                    optional_missing.append(package)
            else:
                __import__(package.replace('google.oauth2', 'google.oauth2.service_account'))
                print_check(f"Package '{package}' installed - {description}", True)
        except ImportError:
            print_check(f"Package '{package}' NOT installed - {description}", False)
            all_installed = False
    
    if not all_installed:
        print(f"\n{YELLOW}To install missing packages:{RESET}")
        print("  pip install -r requirements.txt")
    
    return all_installed


# ============================================================================
# SECTION 2: PROJECT STRUCTURE
# ============================================================================

def check_folders():
    """Check if required folders exist"""
    required_folders = [
        ('config', 'Configuration files', True),
        ('auth', 'Authentication modules', True),
        ('data_fetcher', 'Data fetching modules', True),
        ('indicators', 'Technical indicators', True),
        ('storage', 'Data storage modules', True),
        ('utils', 'Utility modules', True),
        ('credentials', 'Sensitive files (gitignored)', True),
        ('logs', 'Application logs (gitignored)', True),
        ('scripts', 'Utility scripts', True),
    ]
    
    all_exist = True
    for folder, description, required in required_folders:
        if os.path.isdir(folder):
            print_check(f"Folder '{folder}' exists - {description}", True)
        else:
            print_check(f"Folder '{folder}' NOT found - {description}", False)
            all_exist = False
            if folder in ['credentials', 'logs', 'scripts']:
                print_info(f"Create with: mkdir {folder}")
    
    return all_exist


def check_project_files():
    """Check if all required files exist"""
    required_files = [
        ('config/settings.py', 'Application settings', True),
        ('config/env_loader.py', 'Environment loader', True),
        ('main.py', 'Main pipeline', True),
        ('requirements.txt', 'Dependencies list', True),
        ('flask_app.py', 'Flask app (deployment)', False),
        ('.gitignore', 'Git ignore file', False),
    ]
    
    all_good = True
    for filepath, description, required in required_files:
        if os.path.isfile(filepath):
            print_check(f"File '{filepath}' exists - {description}", True)
        else:
            if required:
                print_check(f"File '{filepath}' NOT found - {description}", False)
                all_good = False
            else:
                print_warning(f"File '{filepath}' NOT found - {description}")
                print_info("Optional but recommended")
    
    return all_good


# ============================================================================
# SECTION 3: CREDENTIALS
# ============================================================================

def check_credentials():
    """Check if credentials are properly configured"""
    all_good = True
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config import env_loader
        
        # Check Upstox credentials
        upstox_checks = [
            ('UPSTOX_API_KEY', env_loader.UPSTOX_API_KEY, 'API Key'),
            ('UPSTOX_API_SECRET', env_loader.UPSTOX_API_SECRET, 'API Secret'),
            ('UPSTOX_CLIENT_ID', env_loader.UPSTOX_CLIENT_ID, 'Client ID'),
            ('UPSTOX_TOTP_SECRET', env_loader.UPSTOX_TOTP_SECRET, 'TOTP Secret'),
        ]
        
        for name, value, desc in upstox_checks:
            if value and value not in ['your_api_key_here', 'your_api_secret_here', 'your_totp_secret_here']:
                print_check(f"Upstox {desc} configured", True)
            else:
                print_check(f"Upstox {desc} NOT configured", False)
                all_good = False
        
        # Check Google credentials
        if env_loader.GOOGLE_SHEET_ID and env_loader.GOOGLE_SHEET_ID != "your_google_sheet_id_here":
            print_check("Google Sheet ID configured", True)
        else:
            print_check("Google Sheet ID NOT configured", False)
            all_good = False
        
        # Check Flask secret key (for deployment)
        if hasattr(env_loader, 'FLASK_SECRET_KEY'):
            if env_loader.FLASK_SECRET_KEY and len(env_loader.FLASK_SECRET_KEY) >= 20:
                if env_loader.FLASK_SECRET_KEY != "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY":
                    print_check("Flask Secret Key configured (for deployment)", True)
                else:
                    print_warning("Flask Secret Key is placeholder value")
                    print_info("Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
            else:
                print_warning("Flask Secret Key NOT configured or too short")
                print_info("Required for deployment, optional for local use")
        
        if not all_good:
            print(f"\n{YELLOW}To configure credentials:{RESET}")
            print("  Option 1: Create .env file (recommended)")
            print("  Option 2: Create config/credentials.py")
            print("  Option 3: Set system environment variables")
        
        return all_good
        
    except ImportError as e:
        print_check(f"Failed to load credentials: {e}", False)
        print_info("Create .env file or config/credentials.py")
        return False


def check_service_account():
    """Check if service account JSON file exists and is valid"""
    sa_file = "credentials/service_account.json"
    
    if not os.path.exists(sa_file):
        print_check(f"Service account file NOT found at: {sa_file}", False)
        print_info("Download from Google Cloud Console and place in credentials/ folder")
        print_info("Steps:")
        print_info("  1. Go to Google Cloud Console")
        print_info("  2. Create service account or use existing")
        print_info("  3. Download JSON key file")
        print_info("  4. Save as credentials/service_account.json")
        return False
    
    try:
        with open(sa_file, 'r') as f:
            data = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            print_check(f"Service account file missing fields: {missing}", False)
            return False
        
        print_check("Service account file is valid", True)
        print_info(f"Email: {data.get('client_email')}")
        print_warning("Remember to share your Google Sheet with this email (Editor access)!")
        return True
        
    except json.JSONDecodeError:
        print_check("Service account file is not valid JSON", False)
        return False
    except Exception as e:
        print_check(f"Error reading service account file: {e}", False)
        return False


# ============================================================================
# SECTION 4: RUNTIME STATUS
# ============================================================================

def check_token_file():
    """Check if token file exists (informational)"""
    token_file = "credentials/upstox_token.json"
    
    if os.path.exists(token_file):
        print_warning(f"Existing Upstox token found at {token_file}")
        print_info("Token will be validated before use")
        print_info("If expired, authentication flow will run automatically")
    else:
        print_warning("No existing Upstox token found")
        print_info("Authentication flow will run on first execution")
        print_info(f"Token will be saved to {token_file}")


def check_gitignore():
    """Check if .gitignore exists and has correct rules"""
    if not os.path.exists('.gitignore'):
        print_warning(".gitignore file NOT found")
        print_info("Create .gitignore to prevent committing sensitive files")
        return False
    
    try:
        with open('.gitignore', 'r') as f:
            content = f.read()
        
        required_patterns = ['credentials/', 'logs/', '.env']
        missing = [p for p in required_patterns if p not in content]
        
        if missing:
            print_warning(f".gitignore missing patterns: {missing}")
            print_info("Add these to prevent committing sensitive files")
            return False
        
        print_check(".gitignore file exists with correct patterns", True)
        return True
        
    except Exception as e:
        print_warning(f"Error reading .gitignore: {e}")
        return False


# ============================================================================
# SECTION 5: DEPLOYMENT CHECKS
# ============================================================================

def check_deployment_readiness():
    """Check if ready for deployment to PythonAnywhere"""
    print_header("DEPLOYMENT READINESS (Optional for local use)")
    
    deployment_ready = True
    
    # Check Flask app
    if os.path.exists('flask_app.py'):
        print_check("flask_app.py exists", True)
    else:
        print_warning("flask_app.py NOT found")
        print_info("Required for PythonAnywhere deployment")
        deployment_ready = False
    
    # Check Flask installation
    try:
        import flask
        print_check(f"Flask installed (version {flask.__version__})", True)
    except ImportError:
        print_warning("Flask NOT installed")
        print_info("Install with: pip install Flask")
        deployment_ready = False
    
    # Check webhook URL configuration
    try:
        from config import env_loader
        if hasattr(env_loader, 'WEBHOOK_URL'):
            if 'pythonanywhere.com' in env_loader.WEBHOOK_URL or 'localhost' in env_loader.WEBHOOK_URL:
                print_check(f"Webhook URL configured: {env_loader.WEBHOOK_URL}", True)
            else:
                print_warning(f"Webhook URL may be incorrect: {env_loader.WEBHOOK_URL}")
        else:
            print_warning("Webhook URL NOT configured")
            print_info("Set WEBHOOK_URL in .env or config/credentials.py")
    except:
        pass
    
    return deployment_ready


def generate_deployment_urls():
    """Generate URLs for deployment (PythonAnywhere + cron-job.org)"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config import env_loader
        
        secret = getattr(env_loader, 'FLASK_SECRET_KEY', 'YOUR_SECRET_KEY')
        base_url = getattr(env_loader, 'FLASK_BASE_URL', 'https://yourusername.pythonanywhere.com')
        
        print_header("DEPLOYMENT URLS (For PythonAnywhere + cron-job.org)")
        
        print(f"{YELLOW}Token Request URL:{RESET}")
        print(f"  {base_url}/request-token?secret={secret}")
        
        print(f"\n{YELLOW}Run Job URL:{RESET}")
        print(f"  {base_url}/run-job?secret={secret}")
        
        print(f"\n{YELLOW}Token Status URL:{RESET}")
        print(f"  {base_url}/token-status?secret={secret}")
        
        print(f"\n{YELLOW}Webhook URL (for Upstox app config):{RESET}")
        print(f"  {base_url}/upstox-webhook-v2")
        
        print(f"\n{YELLOW}Recommended Cron Schedule (cron-job.org):{RESET}")
        print("  Token Request:  8:00 AM IST (2:30 AM UTC) - Daily")
        print("  Token Retry 1:  8:30 AM IST (3:00 AM UTC) - Daily")
        print("  Token Retry 2:  9:00 AM IST (3:30 AM UTC) - Daily")
        print("  Data Fetch 1:   9:15 AM IST (3:45 AM UTC) - Daily")
        print("  Data Fetch 2:  11:20 AM IST (5:50 AM UTC) - Daily")
        print("  Data Fetch 3:   1:25 PM IST (7:55 AM UTC) - Daily")
        print("  Data Fetch 4:   3:30 PM IST (10:00 AM UTC) - Daily")
        
    except Exception as e:
        print_warning(f"Could not generate deployment URLs: {e}")


# ============================================================================
# MAIN VERIFICATION
# ============================================================================

def main():
    """Run all checks"""
    print(f"\n{GREEN}{'=' * 60}{RESET}")
    print(f"{GREEN}UPSTOX SUPERTREND - COMPREHENSIVE VERIFICATION{RESET}")
    print(f"{GREEN}{'=' * 60}{RESET}")
    
    all_passed = True
    
    # Section 1: Python Environment
    print_header("1. PYTHON ENVIRONMENT")
    all_passed &= check_python_version()
    deps_ok = check_dependencies()
    all_passed &= deps_ok
    
    # Section 2: Project Structure
    print_header("2. PROJECT STRUCTURE")
    all_passed &= check_folders()
    all_passed &= check_project_files()
    
    # Section 3: Credentials
    print_header("3. CREDENTIALS CONFIGURATION")
    creds_ok = check_credentials()
    all_passed &= creds_ok
    sa_ok = check_service_account()
    all_passed &= sa_ok
    
    # Section 4: Runtime Status
    print_header("4. RUNTIME STATUS")
    check_token_file()  # Informational only
    check_gitignore()    # Warning only
    
    # Section 5: Deployment Readiness
    deployment_ready = check_deployment_readiness()
    
    # Generate deployment URLs if configured
    if deployment_ready:
        generate_deployment_urls()
    
    # Final Summary
    print_header("VERIFICATION SUMMARY")
    
    if all_passed:
        print(f"{GREEN}✓ ALL ESSENTIAL CHECKS PASSED!{RESET}\n")
        print("Your local setup is ready. You can now run:")
        print(f"  {GREEN}python main.py{RESET}")
        
        if deployment_ready:
            print(f"\n{GREEN}✓ DEPLOYMENT CHECKS ALSO PASSED!{RESET}")
            print("You're ready to deploy to PythonAnywhere.")
        else:
            print(f"\n{YELLOW}⚠ DEPLOYMENT: Some optional checks failed{RESET}")
            print("For local use only, this is fine.")
            print("For deployment, install Flask and configure webhook URLs.")
    else:
        print(f"{RED}✗ SOME CHECKS FAILED{RESET}\n")
        print("Please fix the issues above before running the pipeline.")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure credentials (.env or config/credentials.py)")
        print("  3. Add credentials/service_account.json")
        print("  4. Share Google Sheet with service account email")
    
    print(f"\n{BLUE}{'=' * 60}{RESET}\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())