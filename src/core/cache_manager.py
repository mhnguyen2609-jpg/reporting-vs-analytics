
import streamlit as st
import os
import json
import hashlib
from pathlib import Path
from src.utils.drive_adapter import GoogleDriveClient
from src.utils.file_scanner import scan_drive_files, scan_project_files
from src.core.calculator import calculate_aggregates
from src.utils.helpers import natural_sort_key

# Initialize Drive Client
@st.cache_resource
def get_drive_client_v3():
    return GoogleDriveClient()

drive_client = get_drive_client_v3()

# ============================================================
# HELPER FUNCTIONS (DRIVE)
# ============================================================
@st.cache_data(ttl=300)
def get_available_years_drive(root_id):
    if not root_id: return {}, []
    try:
        # 1. Try to list subfolders (Standard Root Structure)
        folders = drive_client.list_folders(root_id)
        years_map = {f['name']: f['id'] for f in folders if f['name'].isdigit()}
        
        # 2. Fallback: Check if the provided ID IS the Year Folder itself
        if not years_map:
            root_meta = drive_client.get_file_metadata(root_id)
            name = root_meta.get('name', '')
            if name.isdigit():
                years_map = {name: root_id}
                st.toast(f"ℹ️ Đã phát hiện link trực tiếp đến năm {name}")

        years_sorted = sorted(years_map.keys(), reverse=True)
        return years_map, years_sorted
    except Exception as e:
        st.error(f"Lỗi khi tải danh sách năm: {e}")
        return {}, []

@st.cache_data(ttl=300)
def get_contracts_for_year_drive(year_folder_id):
    if not year_folder_id: return {}, []
    try:
        folders = drive_client.list_folders(year_folder_id)
        contracts_map = {f['name']: f['id'] for f in folders}
        contracts_sorted = sorted(contracts_map.keys(), key=natural_sort_key)
        return contracts_map, contracts_sorted
    except Exception as e:
        st.error(f"Lỗi khi tải danh sách hợp đồng: {e}")
        return {}, []

def load_data_from_drive(contract_folder_id, progress_callback=None):
    """
    Downloads all Excel files in the contract folder and returns list of file dicts with 'content'.
    Checks DETAILS CACHE first for instant access.
    """
    # 1. Check Cache
    if 'details_cache' in st.session_state and contract_folder_id in st.session_state.details_cache:
        cached_files = st.session_state.details_cache.get(contract_folder_id, [])
        if cached_files:
            # Decode base64 strings back to bytes/BytesIO
            import base64
            decoded_files = []
            for f in cached_files:
                new_f = f.copy()
                content = f.get('content')
                if isinstance(content, str):
                    try:
                        new_f['content'] = base64.b64decode(content)
                    except:
                        pass # Keep as is if decode fails
                decoded_files.append(new_f)
            print(f"[CACHE HIT] Loaded details for {contract_folder_id}")
            return decoded_files

    files_meta = scan_drive_files(drive_client, contract_folder_id)
    results = []
    total = len(files_meta)
    
    for i, f in enumerate(files_meta):
        if progress_callback:
            progress_callback(i / total if total > 0 else 1.0, f"Đang tải: {f['filename']}")
            
        content = drive_client.read_excel(f['file_id'])
        if content:
            f['content'] = content
            results.append(f)
            
    if progress_callback: progress_callback(1.0, "Hoàn tất!")
    return results

# ============================================================
# SHARED CACHE (Persisted on Google Drive)
# ============================================================
# Local cache directory (temporary, fallback)
CACHE_DIR = Path("/tmp/streamlit_cache") if os.path.exists("/tmp") else Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)

CACHE_DATA_FILENAME = "_cache_data.json"
CACHE_TIMESTAMPS_FILENAME = "_cache_timestamps.json"

def get_cache_path(year: str) -> Path:
    return CACHE_DIR / f"data_{year}.json"

def get_timestamps_path(year: str) -> Path:
    return CACHE_DIR / f"timestamps_{year}.json"

def get_details_cache_path(year: str) -> Path:
    return CACHE_DIR / f"details_{year}.json"

def save_shared_cache(year: str, data: list, timestamps: dict, details: dict, year_folder_id: str = None):
    """Save data to shared cache - local + Google Sheets + Details JSON."""
    
    def json_default(obj):
        import numpy as np
        import base64
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
            np.int16, np.int32, np.int64, np.uint8,
            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    try:
        # 1. Save locally first (for quick access)
        with open(get_cache_path(year), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, default=json_default)
        with open(get_timestamps_path(year), 'w', encoding='utf-8') as f:
            json.dump(timestamps, f, ensure_ascii=False, default=json_default)
        
        # 2. Save to Google Sheets (for persistence)
        if year_folder_id and drive_client and drive_client.service:
            # 2a. Save Main Data to Sheets
            sheet_title = f"CACHE_DB_{year}"
            
            # Find or Create Sheet
            spreadsheet_id = drive_client.find_file_in_folder(year_folder_id, sheet_title)
            if not spreadsheet_id:
                spreadsheet_id = drive_client.create_sheet(year_folder_id, sheet_title)
            
            if spreadsheet_id:
                # Resolve Sheet Name Dynamically
                sheet_name = drive_client.get_first_sheet_title(spreadsheet_id) or "Sheet1"
                safe_sheet_name = f"'{sheet_name}'" if " " in sheet_name else sheet_name

                # Prepare Data for Sheet (Flatten to 2D array)
                data_values = []
                if data:
                    header = list(data[0].keys())
                    data_values.append(header)
                    for row in data:
                        data_values.append([str(row.get(k, '')) for k in header])
                
                try:
                    drive_client.clear_sheet_range(spreadsheet_id, f"{safe_sheet_name}!A1:Z")
                    drive_client.write_sheet_data(spreadsheet_id, f"{safe_sheet_name}!A1", data_values)
                    
                    # Save Timestamps in AA1
                    ts_json = json.dumps(timestamps, default=json_default)
                    drive_client.write_sheet_data(spreadsheet_id, f"{safe_sheet_name}!AA1", [['METADATA_TIMESTAMPS', ts_json]])
                    
                    print(f"[OK] Cache saved to Sheets: {sheet_title} ({sheet_name})")
                except Exception as e:
                    print(f"Save Sheet Data Error: {e}")
                    st.error(f"Lỗi khi lưu vào Sheet: {e}")
                
            else:
                 st.error(f"Failed to create/find spreadsheet '{sheet_title}' (ID is None)")

            # 2b. Save Details Cache to JSON File (DETAILS_CACHE_{YEAR}.json)
            if details:
                details_filename = f"DETAILS_CACHE_{year}.json"
                json_content = json.dumps(details, default=json_default, ensure_ascii=False)
                drive_client.upload_json_file(year_folder_id, details_filename, json_content)
                print(f"[OK] Details cache saved: {details_filename}")

            st.toast(f"✅ Cache (Bảng + Chi tiết) đã được lưu!", icon='💾')
        else:
             st.error("Cannot save cache: Google Drive Service not initialized!")
        return True
    except Exception as e:
        print(f"Cache save error: {e}")
        st.error(f"Lỗi khi lưu Cache: {e}")
        return False

def load_shared_cache(year: str, year_folder_id: str = None) -> tuple:
    """
    Load data from shared cache. 
    Priority: 1. Local cache (fast), 2. Google Sheets + Drive JSON (persistent)
    Returns (data, timestamps, details) or (None, None, None).
    """
    # 1. Try local cache first
    try:
        cache_path = get_cache_path(year)
        ts_path = get_timestamps_path(year)
        details_path = get_details_cache_path(year)
        
        if cache_path.exists() and ts_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with open(ts_path, 'r', encoding='utf-8') as f:
                timestamps = json.load(f)
            
            details = {}
            if details_path.exists():
                try:
                    with open(details_path, 'r', encoding='utf-8') as f:
                        details = json.load(f)
                except Exception as e:
                    print(f"Local details cache error: {e}")
            
            return data, timestamps, details
    except Exception as e:
        print(f"Local cache load error: {e}")
    
    # 2. Try Google Sheets cache (if local not found)
    if year_folder_id and drive_client and drive_client.service:
        try:
            sheet_title = f"CACHE_DB_{year}"
            spreadsheet_id = drive_client.find_file_in_folder(year_folder_id, sheet_title)
            
            if spreadsheet_id:
                # Resolve Sheet Name Dynamically
                sheet_name = drive_client.get_first_sheet_title(spreadsheet_id) or "Sheet1"
                safe_sheet_name = f"'{sheet_name}'" if " " in sheet_name else sheet_name
                
                # Read Data from Sheet
                try:
                    raw_values = drive_client.read_sheet_data(spreadsheet_id, f"{safe_sheet_name}!A:Z")
                    
                    if raw_values and len(raw_values) > 1:
                        headers = raw_values[0]
                        data = []
                        for row in raw_values[1:]:
                            if not row: continue
                            item = {}
                            for i, h in enumerate(headers):
                                if i < len(row):
                                    item[h] = row[i]
                                else:
                                    item[h] = ""
                            data.append(item)
                        
                        # Read Timestamps from AA1
                        ts_values = drive_client.read_sheet_data(spreadsheet_id, f"{safe_sheet_name}!AA1")
                        timestamps = {}
                        if ts_values and len(ts_values) > 0 and len(ts_values[0]) > 1:
                            try:
                                ts_json = ts_values[0][1] # METADATA_TIMESTAMPS, {json}
                                timestamps = json.loads(ts_json)
                            except:
                                print("Error parsing timestamps JSON from Sheet")
                        
                        # Read Details Cache from Drive JSON
                        details = {}
                        details_filename = f"DETAILS_CACHE_{year}.json"
                        details_file_id = drive_client.find_file_in_folder(year_folder_id, details_filename)
                        if details_file_id:
                             details = drive_client.read_json_file(details_file_id) or {}
                             print(f"[OK] Loaded Details Cache: {len(details)} items")

                        # Save to local cache for faster access next time
                        with open(get_cache_path(year), 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False)
                        with open(get_timestamps_path(year), 'w', encoding='utf-8') as f:
                            json.dump(timestamps, f, ensure_ascii=False)
                        if details:
                            with open(get_details_cache_path(year), 'w', encoding='utf-8') as f:
                                json.dump(details, f, ensure_ascii=False)
                        
                        print(f"[OK] Cache loaded from Sheets: {sheet_title} ({sheet_name})")
                        return data, timestamps, details
                except Exception as e:
                    print(f"Read Sheet Data Error: {e}")
                    # Continue without cache if sheet read fails
        except Exception as e:
            print(f"Drive cache load error: {e}")
    
    return None, None, None

def is_cache_valid(year: str, current_timestamps: dict, year_folder_id: str = None) -> bool:
    """Check if cached timestamps match current timestamps."""
    _, cached_ts, _ = load_shared_cache(year, year_folder_id)
    if cached_ts is None:
        return False
    return cached_ts == current_timestamps

def load_all_contracts_data_logic(selected_year, years_map, force_reload=False, progress_callback=None):
    """
    Smart caching loader that checks modification times before loading.
    Uses SHARED cache - all users see the same cached data.
    Only reloads contracts that have been modified since last load.
    Also caches DETAILED file lists for instant timeline access.
    """
    year_id = years_map.get(str(selected_year))
    if not year_id: return []
    
    contracts_map, contracts_list = get_contracts_for_year_drive(year_id)
    categories = ['CAD', 'CNC', 'VÁN', 'VẬT TƯ', 'VẬT TƯ ƯU TIÊN']
    
    # Check SHARED cache first (from Drive or local)
    cached_data, cached_timestamps, cached_details = load_shared_cache(str(selected_year), year_id)
    
    # Get current modification times for all contracts
    contract_ids = list(contracts_map.values())
    
    if progress_callback: progress_callback(0.05, "Đang kiểm tra thay đổi...")
    
    current_timestamps = drive_client.get_folder_modified_times(contract_ids)
    
    # Determine which contracts need to be reloaded
    contracts_to_load = []
    if force_reload or not cached_data:
        contracts_to_load = contracts_list
    elif not cached_details:
        # If we have data but NO details (upgrade scenario), we must reload to generate details
        contracts_to_load = contracts_list
        st.toast("⚠️ Đang cập nhật Cache Chi tiết mới...", icon="ℹ️")
    else:
        cached_ts_dict = cached_timestamps if cached_timestamps else {}
        for contract_name in contracts_list:
            contract_id = contracts_map[contract_name]
            old_ts = cached_ts_dict.get(contract_id, '')
            new_ts = current_timestamps.get(contract_id, '')
            if old_ts != new_ts:
                contracts_to_load.append(contract_name)
    
    if progress_callback: progress_callback(0.1, f"Cần cập nhật {len(contracts_to_load)} hợp đồng...")

    # Initialize updated collections
    updated_details = cached_details if cached_details and not force_reload else {}

    # If nothing changed, use cached data
    if not contracts_to_load and cached_data:
        if progress_callback: progress_callback(1.0, "Dữ liệu đã được cache!")
        st.toast("✅ Dữ liệu không thay đổi, dùng cache CHUNG!")
        # Update session state details cache
        st.session_state.details_cache = updated_details
        return cached_data
    
    # Show what we're doing
    if contracts_to_load and len(contracts_to_load) < len(contracts_list):
        st.toast(f"🔄 Đang cập nhật {len(contracts_to_load)} hợp đồng đã thay đổi...")
    
    # Build result - start with cached data if partial reload
    all_rows = []
    
    if cached_data and not force_reload:
        for row in cached_data:
            if row['contract'] not in contracts_to_load:
                all_rows.append(row)
    
    total_to_load = len(contracts_to_load)
    if total_to_load == 0:
        st.session_state.details_cache = updated_details
        if progress_callback: progress_callback(1.0, "Hoàn tất!")
        return all_rows
    
    for idx, contract_name in enumerate(contracts_to_load):
        contract_id = contracts_map[contract_name]
        
        # Calculate Progress: Start from 10% (0.1), distribute remaining 90%
        current_progress = 0.1 + (idx / total_to_load) * 0.8
        if progress_callback:
            progress_callback(current_progress, f"Đang xử lý: {contract_name}")
        
        # Load data (files + content)
        files = load_data_from_drive(contract_id)
        
        # UPDATE DETAILS CACHE
        if files:
            updated_details[contract_id] = files
            
        aggs = calculate_aggregates(files) if files else {}
        
        for cat in categories:
            agg_key = cat
            if cat == 'VÁN': agg_key = 'VAN'
            if cat == 'VẬT TƯ': agg_key = 'VAT_TU'
            if cat == 'VẬT TƯ ƯU TIÊN': agg_key = 'VAT_TU_UU_TIEN'
            
            data = aggs.get(agg_key, {'TC': 0, 'TT': 0, 'percent': 0, 'nhom_hang_tc': 0, 'nhom_hang_tt': 0, 'nhom_percent': 0})
            
            all_rows.append({
                'contract': contract_name,
                'category': cat,
                'tc': data['TC'],
                'tt': data['TT'],
                'percent': data['percent'],
                'nhom_hang_tc': data.get('nhom_hang_tc', 0),
                'nhom_hang_tt': data.get('nhom_hang_tt', 0),
                'nhom_percent': data.get('nhom_percent', 0)
            })
    
    # Update Session State Details Cache
    st.session_state.details_cache = updated_details
    
    if progress_callback: progress_callback(0.95, "Đang lưu cache...")

    # Save to SHARED cache (local + Drive for persistence)
    save_shared_cache(str(selected_year), all_rows, current_timestamps, updated_details, year_id)
    # Also update session state for quick access
    st.session_state.cache_loaded_year = str(selected_year)
            
    if progress_callback: progress_callback(1.0, "Hoàn tất!")
    return all_rows

# ============================================================
# HELPER FUNCTIONS (LOCAL LEGACY)
# ============================================================
def get_available_years_local(root_path):
    if not os.path.exists(root_path): return []
    try:
        return sorted([d for d in os.listdir(root_path) 
                       if os.path.isdir(os.path.join(root_path, d)) and d.isdigit()], 
                      reverse=True)
    except: return []

def get_contracts_for_year_local(root_path, year):
    year_path = os.path.join(root_path, str(year))
    if not os.path.exists(year_path): return []
    try:
        return sorted([d for d in os.listdir(year_path) 
                       if os.path.isdir(os.path.join(year_path, d))], key=natural_sort_key)
    except: return []

def load_all_contracts_data_local(root_path, year, progress_callback=None):
    contracts = get_contracts_for_year_local(root_path, year)
    categories = ['CAD', 'CNC', 'VÁN', 'VẬT TƯ', 'VẬT TƯ ƯU TIÊN']
    
    # 1. Initialize Maps
    local_contracts_map = {}
    for c in contracts:
        local_contracts_map[c] = os.path.join(root_path, str(year), c)

    # 2. Check SHARED Cache
    cached_data, cached_timestamps, cached_details = load_shared_cache(str(year))
    
    # 3. Check Modification Times (Local)
    contracts_to_load = []
    current_timestamps = {}
    
    # Use cached collections as base to preserve Drive data if any
    updated_timestamps = cached_timestamps.copy() if cached_timestamps else {}
    updated_details = cached_details.copy() if cached_details else {}
    
    if progress_callback: progress_callback(0.05, "Đang kiểm tra thay đổi (Local)...")
    
    for contract in contracts:
        c_path = local_contracts_map[contract]
        # Get directory mtime
        try:
            mtime = os.path.getmtime(c_path)
            # Find max mtime of files inside to be more accurate? 
            # For speed, dir mtime might suffice, or logic from file_scanner?
            # Let's stick to dir mtime for now or finding newest file.
            # Dir mtime changes when file added/removed. Content change? Not always.
            # Safe approach: recursive mtime check? Too slow.
            # Let's use dir mtime.
            ts_str = str(mtime)
        except:
            ts_str = "0"
            
        current_timestamps[c_path] = ts_str
        updated_timestamps[c_path] = ts_str # Update current
        
        # Compare with cache (using Path as ID)
        old_ts = cached_timestamps.get(c_path, '') if cached_timestamps else ''
        
        if old_ts != ts_str:
            contracts_to_load.append(contract)
        elif not cached_details or c_path not in cached_details:
             # Also reload if details are missing
             contracts_to_load.append(contract)

    # 4. Filter Cached Data
    all_rows = []
    if cached_data:
        # Keep rows that are NOT in contracts_to_load
        # BUT we must carefully match using Contract Name
        for row in cached_data:
            if row.get('contract') not in contracts_to_load:
                # Issue: If cached_data has "Contract A" from Drive, and we are in Local.
                # If Local also has "Contract A" but it wasn't modified?
                # We use the cached row.
                # If Local "Contract A" IS modified, we skip cached row and reload.
                # This works.
                all_rows.append(row)

    if not contracts_to_load and cached_data:
        if progress_callback: progress_callback(1.0, "Dữ liệu Local đã được cache!")
        st.session_state.contracts_map = local_contracts_map
        st.session_state.details_cache = updated_details
        st.session_state.cache_loaded_year = str(year)
        return all_rows

    # 5. Load Changed Contracts
    total = len(contracts_to_load)
    
    for idx, contract in enumerate(contracts_to_load):
        contract_path = local_contracts_map[contract]
        message = f"Đang quét (Local): {contract}"
        
        ratio = 0.1 + (idx / total) * 0.8 # Scale 10% -> 90%
        if progress_callback:
            progress_callback(ratio, message)
        
        # Scan Files
        files = scan_project_files(contract_path)
        
        # Update Details Cache
        updated_details[contract_path] = files
        
        # Calculate Aggregates
        aggs = calculate_aggregates(files) if files else {}
        
        for cat in categories:
            agg_key = cat
            if cat == 'VÁN': agg_key = 'VAN'
            if cat == 'VẬT TƯ': agg_key = 'VAT_TU'
            if cat == 'VẬT TƯ ƯU TIÊN': agg_key = 'VAT_TU_UU_TIEN'
            
            data = aggs.get(agg_key, {'TC': 0, 'TT': 0, 'percent': 0})
            all_rows.append({
                'contract': contract,
                'category': cat,
                'tc': data['TC'],
                'tt': data['TT'],
                'percent': data['percent'],
                'nhom_hang_tc': data.get('nhom_hang_tc', 0),
                'nhom_hang_tt': data.get('nhom_hang_tt', 0),
                'nhom_percent': data.get('nhom_percent', 0)
            })

    # 6. Save Shared Cache
    if progress_callback: progress_callback(0.95, "Đang lưu cache (Local)...")
    
    # Sort for consistency?
    # all_rows.sort(key=lambda x: natural_sort_key(x['contract'])) # Optional
    
    save_shared_cache(str(year), all_rows, updated_timestamps, updated_details, year_folder_id=None)
    
    if progress_callback: progress_callback(1.0, "Hoàn tất!")
    
    # Update Session State
    st.session_state.contracts_map = local_contracts_map
    st.session_state.details_cache = updated_details
    st.session_state.cache_loaded_year = str(year)
    
    return all_rows
