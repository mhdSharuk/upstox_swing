"""
Test script to verify all Signal Tracker files are complete and correct
Run this before starting the app to catch any issues early
"""

import sys

def test_imports():
    """Test if all modules can be imported"""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    tests = [
        ("streamlit", "Streamlit"),
        ("gspread", "Google Sheets API"),
        ("pandas", "Pandas"),
        ("pytz", "Timezone support"),
        ("config", "Config module"),
        ("data_handler", "Data handler module"),
        ("watchlist_manager", "Watchlist manager module"),
        ("utils", "Utils module"),
    ]
    
    failed = []
    
    for module, name in tests:
        try:
            __import__(module)
            print(f"✅ {name}: OK")
        except ImportError as e:
            print(f"❌ {name}: FAILED - {e}")
            failed.append(name)
    
    return len(failed) == 0, failed


def test_functions():
    """Test if all critical functions exist"""
    print("\n" + "=" * 60)
    print("TESTING FUNCTIONS")
    print("=" * 60)
    
    failed = []
    
    # Test watchlist_manager functions
    try:
        from watchlist_manager import (
            create_watchlist_sheet_if_not_exists,
            is_in_watchlist,
            add_to_watchlist,
            remove_from_watchlist,
            get_watchlist_as_dataframe
        )
        print("✅ watchlist_manager.is_in_watchlist: OK")
        print("✅ watchlist_manager.add_to_watchlist: OK")
        print("✅ watchlist_manager.remove_from_watchlist: OK")
        print("✅ watchlist_manager.get_watchlist_as_dataframe: OK")
    except ImportError as e:
        print(f"❌ watchlist_manager functions: FAILED - {e}")
        failed.append("watchlist_manager")
    
    # Test data_handler functions
    try:
        from data_handler import (
            get_gspread_client,
            fetch_sheet_data,
            get_latest_rows_per_symbol,
            get_supertrend_columns,
            process_signals,
            fetch_watchlist_data,
            clear_cache,
            clear_watchlist_cache_only
        )
        print("✅ data_handler.fetch_sheet_data: OK")
        print("✅ data_handler.process_signals: OK")
        print("✅ data_handler.clear_watchlist_cache_only: OK")
    except ImportError as e:
        print(f"❌ data_handler functions: FAILED - {e}")
        failed.append("data_handler")
    
    # Test utils functions
    try:
        from utils import (
            is_market_hours,
            format_number,
            get_current_timestamp
        )
        print("✅ utils.is_market_hours: OK")
        print("✅ utils.format_number: OK")
    except ImportError as e:
        print(f"❌ utils functions: FAILED - {e}")
        failed.append("utils")
    
    return len(failed) == 0, failed


def test_config():
    """Test if config is properly set up"""
    print("\n" + "=" * 60)
    print("TESTING CONFIGURATION")
    print("=" * 60)
    
    try:
        import config
        
        if config.SPREADSHEET_ID == "YOUR_SPREADSHEET_ID_HERE":
            print("⚠️  SPREADSHEET_ID: NOT SET (still using placeholder)")
            print("   → Update config.py with your actual spreadsheet ID")
            return False
        else:
            print(f"✅ SPREADSHEET_ID: Set ({config.SPREADSHEET_ID[:20]}...)")
        
        print(f"✅ CACHE_TTL_SIGNALS: {config.CACHE_TTL_SIGNALS}s")
        print(f"✅ CACHE_TTL_WATCHLIST: {config.CACHE_TTL_WATCHLIST}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test: FAILED - {e}")
        return False


def test_secrets():
    """Test if secrets are configured (only when Streamlit is available)"""
    print("\n" + "=" * 60)
    print("TESTING SECRETS")
    print("=" * 60)
    
    try:
        import os
        secrets_path = ".streamlit/secrets.toml"
        
        if os.path.exists(secrets_path):
            print(f"✅ secrets.toml: EXISTS")
            
            # Check if it's not empty
            with open(secrets_path, 'r') as f:
                content = f.read()
                if len(content) > 100:
                    print("✅ secrets.toml: Appears to have content")
                    if "gcp_service_account" in content:
                        print("✅ gcp_service_account: Section found")
                    else:
                        print("⚠️  gcp_service_account: Section NOT found")
                        return False
                else:
                    print("⚠️  secrets.toml: File is too small (likely empty)")
                    return False
        else:
            print(f"⚠️  secrets.toml: NOT FOUND at {secrets_path}")
            print("   → Create .streamlit/secrets.toml with your service account")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Secrets test: FAILED - {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("SIGNAL TRACKER - FILE VERIFICATION TEST")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    import_ok, import_failed = test_imports()
    results.append(("Imports", import_ok, import_failed))
    
    function_ok, function_failed = test_functions()
    results.append(("Functions", function_ok, function_failed))
    
    config_ok = test_config()
    results.append(("Configuration", config_ok, []))
    
    secrets_ok = test_secrets()
    results.append(("Secrets", secrets_ok, []))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed, failed in results:
        if passed:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
            if failed:
                for item in failed:
                    print(f"   - {item}")
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("You can now run: streamlit run app.py")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("Please fix the issues above before running the app")
        print("\nCommon fixes:")
        print("1. Run: pip install -r requirements.txt")
        print("2. Update config.py with your SPREADSHEET_ID")
        print("3. Create .streamlit/secrets.toml with service account")
        print("4. Make sure you have the LATEST files from outputs/")
    
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())