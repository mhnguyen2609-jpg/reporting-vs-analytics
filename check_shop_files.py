import sys
import os
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.utils.excel_parser import read_excel_data, find_header_row
from src.utils.file_scanner import identify_source_type

def check_file(path, expected_type):
    print(f"\n--- Checking: {os.path.basename(path)} ---")
    if not os.path.exists(path):
        print("File not found!")
        return

    # Check Identification
    identified = identify_source_type(os.path.basename(path), os.path.basename(os.path.dirname(path)))
    print(f"Identified Type: {identified} (Expected: {expected_type})")

    # Check Header finding
    header_row = find_header_row(path)
    print(f"Header Row Index: {header_row}")

    # Read Raw Header
    df_raw = pd.read_excel(path, header=header_row, nrows=0) 
    print(f"Raw Columns: {df_raw.columns.tolist()}")

    # Read Data using Parser
    df = read_excel_data(path, expected_type)
    if df is not None:
        print(f"Parsed Shape: {df.shape}")
        print(f"Parsed Columns: {df.columns.tolist()}")
        if 'quantity' in df.columns:
            print(f"Total Quantity: {df['quantity'].sum()}")
        else:
            print("MISSING 'quantity' column!")
        
        if 'key' in df.columns:
             print(f"Key Column Found. Sample keys: {df['key'].head(3).tolist()}")
        else:
             print("MISSING 'key' column!")
parent_dir = r"D:\Cong viec\2026"
target_fragment = "NAM O_T2_S03"

if not os.path.exists(parent_dir):
    print(f"Parent dir not found: {parent_dir}")
else:
    print(f"Listing {parent_dir}...")
    found_root = None
    for name in os.listdir(parent_dir):
        print(f" - {repr(name)}")
        if target_fragment in name: # naive partial match
            found_root = os.path.join(parent_dir, name)
            print(f"   -> MATCH! Path: {found_root}")
            break
            
    if found_root:
        print(f"\nScanning found root: {found_root}")
        files_to_check = []
        for root, dirs, filenames in os.walk(found_root):
            if 'SHOP' in root.upper():
                 for name in filenames:
                     if name.lower().endswith('.xlsx') and not name.startswith('~$'):
                         full_path = os.path.join(root, name)
                         expected = 'SHOP_TC' if 'SHOPT' in name.upper() else 'SHOP_TT'
                         files_to_check.append((full_path, expected))
        
        if not files_to_check:
            print("No SHOP files found via walk!")
        
        for p, t in files_to_check:
            check_file(p, t)
    else:
        print(f"Could not find folder matching '{target_fragment}'")
