
from src.utils.drive_adapter import GoogleDriveClient

def test_sheets():
    print("Testing Google Sheets Creation...")
    client = GoogleDriveClient()
    
    if not client.sheets_service:
        print("❌ Sheets Service not initialized. Check SCOPES.")
        return

    # Folder ID for 2026 (from app.py hardcoded or previous context)
    # We can ask user or try to find one. Let's use the one from debugging: '1hn-nFm56a3X24qs3WbweJfx6BqJ9ggr6' (2026)
    folder_id = '1hn-nFm56a3X24qs3WbweJfx6BqJ9ggr6' 
    
    print(f"Target Folder: {folder_id}")
    

    # 1. Try to find existing
    print("1. Searching for existing cache...")
    found_id = client.find_file_in_folder(folder_id, "TEST_SHEET_CACHE")
    if found_id:
        print(f"FOUND existing sheet: {found_id}")
    else:
        print("Sheet not found.")

    # 2. Try to create
    print("2. Attempting to create new Sheet...")
    new_id = client.create_sheet(folder_id, "TEST_SHEET_CACHE")
    
    if new_id:
        print(f"SUCCESS! Created Sheet ID: {new_id}")
        
        # 3. Try to write
        print("3. Writing data...")
        success = client.write_sheet_data(new_id, "Sheet1!A1", [["Hello", "World"], ["Test", "Data"]])
        if success:
            print("Write successful")
        else:
            print("Write failed")
            
    else:
        print("FAILED to create sheet. Likely storage quota or permission issue.")

if __name__ == "__main__":
    test_sheets()
