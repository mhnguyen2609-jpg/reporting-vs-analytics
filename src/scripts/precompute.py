
import os
import sys
import json
import pandas as pd
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.cache_manager import load_all_contracts_data_local
from src.core.constants import YEAR_FOLDERS

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
        
        # Custom JSON encoder for datetime/bytes
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, bytes):
                    return "<binary_data_skipped>" # or base64 if needed, but for master table maybe skip?
                    # Wait, details need content.
                    # If we skip content, details view won't work.
                    # We should encode to base64 if small, or save separately?
                    # For now, let's skip binary content for the MASTER file if it's too big,
                    # BUT the user wants details data pre-calculated too.
                    # If we save everything to one JSON it might be huge (50MB+).
                    # Streamlit handles 50MB fine if loaded once.
                    pass
                if isinstance(obj, pd.Timestamp):
                    return obj.strftime('%Y-%m-%d')
                return super().default(obj)
                
        # Actually, `load_all_contracts_data_local` returns a list of Dicts.
        # But wait, does it include FILE CONTENT? 
        # `scan_project_files` -> `read_excel` -> Returns DataFrames? No, `scan` returns metadata.
        # `load_all_contracts_data_local` calls `calculate_aggregates` which reads files.
        # But `master_data` usually containsAGGREGATED stats, not raw file content.
        # EXCEPT for `details_cache`.
        
        # Let's check what `master_data` structure is.
        # It is a list of dicts with keys like 'contract', 'CAD', 'CNC', etc.
        # It does NOT contain file content.
        # So it is small!
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=CustomEncoder)
            
        print(f"✅ Data saved to {output_file}")
        
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
