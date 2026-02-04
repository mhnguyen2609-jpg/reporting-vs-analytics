
import os
import sys
import pandas as pd

# Add src path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'src')))

try:
    from utils.file_scanner import scan_project_files
    from utils.excel_parser import read_excel_data
except ImportError:
    sys.path.append(os.getcwd())
    from src.utils.file_scanner import scan_project_files
    from src.utils.excel_parser import read_excel_data

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))
    except Exception as e:
        print(f"Error printing: {e}")

def debug_cat_files():
    # Hardcoded path to the project found
    root_path = r"D:\Cong viec\2026\049. GE2512002_Loan Mê Linh"
    
    safe_print(f"\nScanning from: {root_path}")
    if not os.path.exists(root_path):
        safe_print(f"ERROR: Path does not exist: {root_path}")
        return

    files = scan_project_files(root_path)
    safe_print(f"Total files found: {len(files)}")
    
    cat_tt_files = [f for f in files if f['source_type'] == 'CAT_TT']
    shop_tc_files = [f for f in files if f['source_type'] == 'SHOP_TC']
    
    cat_keys = set()
    safe_print(f"\n--- LOADING CAT_TT DATA ({len(cat_tt_files)} files) ---")
    for f in cat_tt_files:
        try:
            df = read_excel_data(f['path'], 'CAT_TT')
            if df is not None and 'key' in df.columns and 'ma_hieu' in df.columns:
                 # Filter valid rows
                 valid = df[df['key'].notna() & df['ma_hieu'].notna()]
                 keys = set(valid['key'].astype(str).str.strip())
                 cat_keys.update(keys)
                 safe_print(f"  > {os.path.basename(f['path'])}: Found {len(keys)} valid keys with ma_hieu options.")
                 # Print sample
                 if not valid.empty:
                    safe_print(f"    Sample: {valid[['key', 'ma_hieu']].head(3).to_dict('records')}")
        except Exception as e:
            safe_print(f"  Expected error reading {os.path.basename(f['path'])}: {e}")

    safe_print(f"\nTotal Unique CAT Keys loaded: {len(cat_keys)}")
    safe_print(f"Sample CAT Keys: {list(cat_keys)[:10]}")

    safe_print(f"\n--- CHECKING MATCH WITH SHOP_TC ({len(shop_tc_files)} files) ---")
    match_count = 0
    total_shop_keys = 0
    for f in shop_tc_files:
        try:
            df = read_excel_data(f['path'], 'SHOP_TC')
            if df is not None and 'key' in df.columns:
                shop_keys = set(df['key'].astype(str).str.strip())
                total_shop_keys += len(shop_keys)
                
                matches = shop_keys.intersection(cat_keys)
                match_count += len(matches)
                
                safe_print(f"  > {os.path.basename(f['path'])}: {len(matches)}/{len(shop_keys)} keys have matching CAT data.")
                if len(matches) == 0 and len(shop_keys) > 0:
                     safe_print(f"    WARNING: No matches found! Sample Shop Keys: {list(shop_keys)[:5]}")
        except:
            pass
            
    safe_print(f"\nTotal Shop Keys: {total_shop_keys}")
    safe_print(f"Total Matches: {match_count}")

if __name__ == "__main__":
    debug_cat_files()
