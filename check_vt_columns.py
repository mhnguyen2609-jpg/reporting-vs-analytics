import pandas as pd
import sys
import io
import os

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

vt_path = r"D:\Cong viec\2026\057. 251230_R02_BD_ECO_92_NAM Ô S01 S03\VT"
print(f"Scanning from VT: {vt_path}")

files_to_check = []
for root, dirs, filenames in os.walk(vt_path):
    for f in filenames:
        if f.endswith('.xlsx') and not f.startswith('~$'):
            files_to_check.append(os.path.join(root, f))

for file_path in files_to_check:
    print("-" * 30)
    print(f"File: {os.path.basename(file_path)}")
    try:
        # Read header
        df_temp = pd.read_excel(file_path, header=None, nrows=20)
        header_row = 0
        found_header = False
        
        # Look for typical headers
        for idx, row in df_temp.iterrows():
            row_str = [str(x).lower() for x in row.tolist()]
            if any('số lượng' in x for x in row_str) and any('tên hàng' in x for x in row_str):
                header_row = idx
                print(f"  Header found at row {idx}")
                found_header = True
                break
        
        if found_header:
            df = pd.read_excel(file_path, header=header_row)
            columns = [str(c).lower().strip() for c in df.columns]
            
            # Check for Ma AP
            ma_sp_cols = [c for c in columns if any(k in c for k in ['mã sp', 'mã sản phẩm', 'model', 'product code', 'key', 'ma sp'])]
            
            print(f"  All Columns: {columns}")
            if ma_sp_cols:
                print(f"  ✅ Found 'Mã SP' candidates: {ma_sp_cols}")
                # Show some values
                real_col = df.columns[columns.index(ma_sp_cols[0])]
                print(f"  Sample values: {df[real_col].dropna().unique()[:5]}")
            else:
                print(f"  ❌ No 'Mã SP' column found.")
        else:
            print("  Warning: Could not detect standard header.")
            
    except Exception as e:
        print(f"  Error: {e}")
