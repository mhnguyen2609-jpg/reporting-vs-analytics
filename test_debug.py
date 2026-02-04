import sys
import os
import io
import pandas as pd

# Fix encoding for Windows console (Vietnamese characters)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.utils.file_scanner import scan_project_files
from src.core.config_loader import load_project_identity
from src.core.calculator import calculate_aggregates, build_matrix_table
from src.core.constants import DEFAULT_ROOT_PATH

def run_debug_test(root_path=None):
    if root_path is None:
        root_path = DEFAULT_ROOT_PATH
        
    print(f"--- STARTING DEBUG TEST ON: {root_path} ---")
    
    # 1. Scan Files
    print(f"\n[1] Scanning folders...")
    # Try 2024 or 2025 if exists, or just scan root? 
    # scan_project_files recursively scans. If D:\Cong viec is huge, this might take time.
    # Let's search for a specific year if possible, or just the root level.
    # For safety in test, let's try to find a year folder first.
    
    files = scan_project_files(root_path)
    print(f"Found {len(files)} Excel files.")
    
    if not files:
        print("No files found. Please check the root path.")
        return
        
    # Show first 5 files
    for f in files[:5]:
        print(f" - {f['filename']} -> Type: {f['source_type']}")
        
    # 2. Config Loader (Find first config.xlsx)
    print(f"\n[2] Testing Config Loader...")
    config_file = next((f for f in files if f['filename'].lower() == 'config.xlsx'), None)
    if config_file:
        print(f"Found config at: {config_file['path']}")
        identity = load_project_identity(config_file['path'])
        print(f"Identity: {identity}")
    else:
        print("No config.xlsx found in scanned files.")

    # 3. Aggregation
    print(f"\n[3] Testing Aggregation...")
    aggs = calculate_aggregates(files)
    for cat, data in aggs.items():
        print(f"Category: {cat} | TC: {data['TC']} | TT: {data['TT']} | %: {data['percent']:.2f}%")
        
    # 4. Matrix
    print(f"\n[4] Testing Matrix Building...")
    matrix_df = build_matrix_table(files)
    if not matrix_df.empty:
        print(f"Matrix Shape: {matrix_df.shape}")
        print("Sample Data (Head 5):")
        print(matrix_df.head(5))
    else:
        print("Matrix empty.")
        
    print("\n--- TEST FINISHED ---")

if __name__ == "__main__":
    # Allow user to pass path via arg or use default
    target = r"D:\Cong viec" # Manual override for testing if needed
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    if os.path.exists(target):
        run_debug_test(target)
    else:
        print(f"Path {target} does not exist. Using current dir for dummy test?")
        # Just create dummy structure? No, let's fail gracefully.
        print("Target path not found.")
