import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

# Read the actual Excel file to see raw data
file_path = r'D:\Cong viec\2026\1. TC251230_NAM Ô_T2_S03\VT\CNC\SHOP\1. TC251230_SHOP NAM Ô_T2_S03.xlsx'

# Read without header auto-detection
df_raw = pd.read_excel(file_path, header=None, nrows=25)
print("=== RAW DATA (First 25 rows) ===")
print(df_raw.to_string())

print("\n\n=== Column names row (usually row 10-15) ===")
for idx, row in df_raw.iterrows():
    row_values = [str(v).strip() for v in row.values if pd.notna(v)]
    if any(kw in ' '.join(row_values).lower() for kw in ['số lượng', 'mã sp', 'tên hàng']):
        print(f"Row {idx}: {row_values}")
