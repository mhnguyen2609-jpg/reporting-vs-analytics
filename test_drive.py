"""
Test script to verify Google Drive API access.
Run with: python test_drive.py
"""
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_PATH = 'credentials.json'
# The folder ID from the user's link: https://drive.google.com/drive/folders/1hn-nFm56a3X24qs3WbweJfx6BqJ9ggr6
FOLDER_ID = '1hn-nFm56a3X24qs3WbweJfx6BqJ9ggr6'

def main():
    print(f"Testing Drive API access...")
    print(f"Credentials file: {CREDENTIALS_PATH}")
    print(f"Folder ID: {FOLDER_ID}")
    print("-" * 50)
    
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        print("[OK] Credentials loaded successfully")
        print(f"    Service Account Email: {creds.service_account_email}")
    except Exception as e:
        print(f"[ERROR] Failed to load credentials: {e}")
        return
    
    try:
        service = build('drive', 'v3', credentials=creds)
        print("[OK] Drive service built successfully")
    except Exception as e:
        print(f"[ERROR] Failed to build service: {e}")
        return
    
    # Test 1: Get folder metadata
    print("-" * 50)
    print("Test 1: Getting folder metadata...")
    try:
        folder = service.files().get(fileId=FOLDER_ID, fields='id, name, mimeType').execute()
        print(f"[OK] Folder found!")
        print(f"    Name: {folder.get('name')}")
        print(f"    ID: {folder.get('id')}")
        print(f"    Type: {folder.get('mimeType')}")
    except Exception as e:
        print(f"[ERROR] Cannot access folder: {e}")
        print("")
        print(">>> SOLUTION: You need to share the folder with the Service Account email!")
        print(f">>> Share this folder with: {creds.service_account_email}")
        return
    
    # Test 2: List subfolders
    print("-" * 50)
    print("Test 2: Listing subfolders...")
    try:
        query = f"'{FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields='files(id, name)').execute()
        folders = results.get('files', [])
        print(f"[OK] Found {len(folders)} subfolders:")
        for f in folders:
            print(f"    - {f['name']} (ID: {f['id']})")
    except Exception as e:
        print(f"[ERROR] Cannot list folders: {e}")
    
    print("-" * 50)
    print("Test complete!")

if __name__ == '__main__':
    main()
