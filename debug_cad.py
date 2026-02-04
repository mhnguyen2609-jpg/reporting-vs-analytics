import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.utils.file_scanner import scan_project_files
from src.core.calculator import calculate_aggregates
from src.utils.excel_parser import read_excel_data

# Test with real contract folder
contract_path = r'D:\Cong viec\2026\1. TC251230_NAM Ô_T2_S03'
files = scan_project_files(contract_path)

print('=== SCANNED FILES ===')
for f in files:
    print(f"{f['source_type']}: {f['filename']}")

print('\n=== CAD-RELATED FILES ===')
cad_files = [f for f in files if 'SHOP' in f['source_type']]
for f in cad_files:
    print(f"{f['source_type']}: {f['path']}")

print('\n=== AGGREGATES ===')
aggs = calculate_aggregates(files) if files else {}
for cat, data in aggs.items():
    print(f'{cat}: TC={data["TC"]}, TT={data["TT"]}, %={data["percent"]:.1f}')

# Deep dive into CAD parsing
print('\n=== CAD DATA DETAILS ===')
for f in cad_files:
    print(f"\nFile: {f['filename']} ({f['source_type']})")
    df = read_excel_data(f['path'], f['source_type'])
    if df is not None:
        print(f"  Columns: {df.columns.tolist()}")
        print(f"  Rows: {len(df)}")
        if 'key' in df.columns and 'quantity' in df.columns:
            print(f"  Sample keys: {df['key'].head(5).tolist()}")
            print(f"  Total quantity: {df['quantity'].sum()}")
        else:
            print(f"  WARNING: Missing key or quantity column!")
    else:
        print(f"  ERROR: Could not parse file!")
