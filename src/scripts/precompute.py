
import os
import sys
import json
import pandas as pd
import base64
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock Streamlit Session State BEFORE importing cache_manager
class MockSessionState(dict):
    def __init__(self):
        self.details_cache = {}
        self.contracts_map = {}
        self.master_data = []

import streamlit as st
if not hasattr(st, 'session_state'):
    st.session_state = MockSessionState()

from src.core.cache_manager import load_all_contracts_data_local
from src.core.constants import YEAR_FOLDERS

# Custom JSON encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
            np.int16, np.int32, np.int64, np.uint8,
            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        if isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        return super().default(obj)

def precompute_data(year=2026, local_root="D:\\Cong viec"):
    print(f"🚀 Starting pre-computation for year {year} at {local_root}")
    
    if not os.path.exists(local_root):
        print(f"❌ Path {local_root} does not exist.")
        return

    # Mock progress callback
    def progress(p, t):
        print(f"[{int(p*100)}%] {t}")

    # Load Data (using Local Logic)
    try:
        data = load_all_contracts_data_local(local_root, year, progress_callback=progress)
        
        # Serialize and Save to JSON
        output_dir = "data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        output_file = os.path.join(output_dir, f"master_data_{year}.json")
        details_file = os.path.join(output_dir, f"details_data_{year}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=CustomEncoder)
            
        # Get Details from Session State
        details = st.session_state.details_cache
        with open(details_file, 'w', encoding='utf-8') as f:
            json.dump(details, f, ensure_ascii=False, cls=CustomEncoder)

        print(f"✅ Data saved to {output_file}")
        print(f"✅ Details saved to {details_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Allow command line args
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="D:\\Cong viec", help="Path to local data")
    parser.add_argument("--year", type=int, default=2026, help="Year to process")
    args = parser.parse_args()
    
    precompute_data(args.year, args.path)
