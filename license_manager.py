import json
import os
import sys

LICENSE_FILE = "licenses.json"

def load_licenses():
    if not os.path.exists(LICENSE_FILE):
        return {}
    with open(LICENSE_FILE, "r") as f:
        return json.load(f)

def verify_license_key(key):
    licenses = load_licenses()
    info = licenses.get(key)
    if info and info.get("valid"):
        return True, info
    return False, None

def prompt_for_license():
    return input("Enter your license key: ").strip()

def require_license():
    key = prompt_for_license()
    valid, info = verify_license_key(key)
    if valid:
        print(f"License valid! Welcome, {info.get('user', 'User')}.")
        return True
    else:
        print("Invalid license key. Exiting.")
        sys.exit(1) 