import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import sys
import math
import io
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.file_scanner import scan_drive_files, scan_project_files
from src.core.calculator import calculate_aggregates, build_matrix_table, get_all_product_details
from src.utils.drive_adapter import GoogleDriveClient
from src.core.constants import DEFAULT_ROOT_PATH

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Dashboard Quản lý Sản xuất (Cloud)",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global CSS for Arial font
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: Arial, sans-serif; }
</style>
""", unsafe_allow_html=True)

import re
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]

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
    except:
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
# Cache is saved to Year folder on Drive for permanent persistence

import json
import hashlib
from pathlib import Path

# Local cache directory (temporary, fallback)
CACHE_DIR = Path("/tmp/streamlit_cache") if os.path.exists("/tmp") else Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)

CACHE_DATA_FILENAME = "_cache_data.json"
CACHE_TIMESTAMPS_FILENAME = "_cache_timestamps.json"

def get_cache_path(year: str) -> Path:
    return CACHE_DIR / f"data_{year}.json"

def get_timestamps_path(year: str) -> Path:
    return CACHE_DIR / f"timestamps_{year}.json"

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
                # Prepare Data for Sheet (Flatten to 2D array)
                # Sheet 1: Data
                data_values = []
                if data:
                    header = list(data[0].keys())
                    data_values.append(header)
                    for row in data:
                        data_values.append([str(row.get(k, '')) for k in header])
                
                drive_client.clear_sheet_range(spreadsheet_id, "Sheet1!A1:Z")
                drive_client.write_sheet_data(spreadsheet_id, "Sheet1!A1", data_values)
                
                # Save Timestamps in AA1
                ts_json = json.dumps(timestamps, default=json_default)
                drive_client.write_sheet_data(spreadsheet_id, "Sheet1!AA1", [['METADATA_TIMESTAMPS', ts_json]])
                
                print(f"[OK] Cache saved to Sheets: {sheet_title}")
                
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

def get_details_cache_path(year: str) -> Path:
    return CACHE_DIR / f"details_{year}.json"

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
                # Read Data from Sheet1
                raw_values = drive_client.read_sheet_data(spreadsheet_id, "Sheet1!A:Z")
                # ... (Parsing logic same as before)
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
                    ts_values = drive_client.read_sheet_data(spreadsheet_id, "Sheet1!AA1")
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
                    
                    print(f"[OK] Cache loaded from Sheets: {sheet_title}")
                    return data, timestamps, details
        except Exception as e:
            print(f"Drive cache load error: {e}")
    
    return None, None, None

def is_cache_valid(year: str, current_timestamps: dict, year_folder_id: str = None) -> bool:
    """Check if cached timestamps match current timestamps."""
    _, cached_ts, _ = load_shared_cache(year, year_folder_id)
    if cached_ts is None:
        return False
    return cached_ts == current_timestamps

def load_all_contracts_data_logic(selected_year, years_map, force_reload=False):
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
    
    status_text = st.empty()
    if not force_reload and cached_data:
        status_text.text("Đang kiểm tra thay đổi...")
    
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
    
    # Initialize updated collections
    updated_details = cached_details if cached_details and not force_reload else {}

    # If nothing changed, use cached data
    if not contracts_to_load and cached_data:
        status_text.text("")
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
    
    # Progress bar
    progress_bar = st.progress(0)
    
    total_to_load = len(contracts_to_load)
    if total_to_load == 0:
        progress_bar.empty()
        status_text.empty()
        st.session_state.details_cache = updated_details
        return all_rows
    
    for idx, contract_name in enumerate(contracts_to_load):
        contract_id = contracts_map[contract_name]
        status_text.text(f"Đang xử lý: {contract_name} ({idx+1}/{total_to_load})")
        progress_bar.progress((idx) / total_to_load)
        
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

    # Save to SHARED cache (local + Drive for persistence)
    save_shared_cache(str(selected_year), all_rows, current_timestamps, updated_details, year_id)
    # Also update session state for quick access
    st.session_state.cache_loaded_year = str(selected_year)
            
    progress_bar.empty()
    status_text.empty()
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

def load_all_contracts_data_local(root_path, year):
    contracts = get_contracts_for_year_local(root_path, year)
    all_rows = []
    categories = ['CAD', 'CNC', 'VÁN', 'VẬT TƯ', 'VẬT TƯ ƯU TIÊN']
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(contracts)
    
    for idx, contract in enumerate(contracts):
        status_text.text(f"Đang quét (Local): {contract} ({idx+1}/{total})")
        progress_bar.progress(idx / total if total > 0 else 0)
        
        contract_path = os.path.join(root_path, str(year), contract)
        files = scan_project_files(contract_path)
        aggs = calculate_aggregates(files) if files else {}
        
        for cat in categories:
            agg_key = cat
            if cat == 'VÁN': agg_key = 'VAN'
            if cat == 'VẬT TƯ': agg_key = 'VAT_TU'
            if cat == 'VẬT TƯ ƯU TIÊN': agg_key = 'VAT_TU_UU_TIEN'
            
            data = aggs.get(agg_key, {'TC': 0, 'TT': 0, 'percent': 0})
            all_rows.append({
                'contract': contract,
                'category': cat, # Display name
                'tc': data['TC'],
                'tt': data['TT'],
                'percent': data['percent'],
                'nhom_hang_tc': data.get('nhom_hang_tc', 0),
                'nhom_hang_tt': data.get('nhom_hang_tt', 0),
                'nhom_percent': data.get('nhom_percent', 0)
            })
            
    progress_bar.empty()
    status_text.empty()
    return all_rows

def get_progress_color(percent):
    """
    Logic màu sắc theo ref_ui_project_overview.md:
    - 100%: Xanh Biển (#1E88E5)
    - 0-99%: Vàng (#FF9800)
    - 0%: Xám (#374151)
    """
    if percent >= 100:
        return '#1E88E5'  # Xanh biển
    elif percent > 0:
        return '#FF9800'  # Vàng
    else:
        return '#374151'  # Xám

def render_master_table_html(data):
    if not data:
        return "<p>Không có dữ liệu.</p>"
    
    # Group data by contract
    contracts_data = {}
    for row in data:
        contract = row['contract']
        if contract not in contracts_data:
            contracts_data[contract] = {}
        contracts_data[contract][row['category']] = row
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { margin: 0; padding: 4px; background: #1a1a2e; }
        .master-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .master-table th, .master-table td {
            border: 1px solid #ffffff;
            padding: 6px 10px;
            color: #ffffff;
            vertical-align: middle;
        }
        .master-table th {
            background: #1a1a2e;
            font-weight: 600;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .master-table td {
            background: #1a1a2e;
        }
        .contract-cell {
            text-align: center;
            font-weight: 500;
        }
        .category-cell {
            text-align: center;
            font-weight: 500;
        }
        .sub-cell {
            text-align: center;
            font-size: 12px;
        }
        .number-cell {
            text-align: center;
        }
        .percent-cell {
            padding: 0 !important;
            position: relative;
            overflow: hidden;
        }
        .progress-wrapper {
            position: relative;
            width: 100%;
            height: 100%;
            min-height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .progress-fill {
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            z-index: 1;
        }
        .progress-text {
            position: relative;
            z-index: 2;
            color: white;
            font-weight: 600;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }
    </style>
    </head>
    <body>
    <table class="master-table">
        <thead>
            <tr>
                <th style="width:20%;">Mã hợp đồng_Tên<br>khách hàng</th>
                <th colspan="2" style="width:25%;">DANH MỤC</th>
                <th style="width:15%;">Khối lượng</th>
                <th style="width:15%;">Hoàn thành</th>
                <th style="width:12%;">%</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # Helper function to render progress bar cell
    def render_progress_cell(percent, tc):
        if tc > 0:
            color = get_progress_color(percent)
            width = min(percent, 100)
            return f'''<td class="percent-cell">
                <div class="progress-wrapper">
                    <div class="progress-fill" style="width:{width}%; background:{color};"></div>
                    <span class="progress-text">{percent:.1f}%</span>
                </div>
            </td>'''
        return '<td class="percent-cell"><div class="progress-wrapper"></div></td>'
    
    # Categories structure: CAD, CNC, VÁN have 1 row; VẬT TƯ, VẬT TƯ ƯU TIÊN have 2 sub-rows
    # Sort contracts Natural Sort (Using global helper)
    sorted_contracts = sorted(contracts_data.keys(), key=natural_sort_key)

    for contract in sorted_contracts:
        cat_data = contracts_data[contract]
        # Total rows per contract: CAD(1) + CNC(1) + VÁN(1) + VẬT TƯ(2) + VẬT TƯ ƯU TIÊN(2) = 7
        total_rows = 7
        first_row = True
        
        # CAD row
        cad = cat_data.get('CAD', {'tc': 0, 'tt': 0, 'percent': 0})
        tc_disp = int(cad['tc']) if cad['tc'] > 0 else ''
        tt_disp = int(cad['tt']) if cad['tt'] > 0 else ''
        html += f'<tr>'
        html += f'<td class="contract-cell" rowspan="{total_rows}">{contract}</td>'
        html += f'<td class="category-cell" colspan="2">CAD</td>'
        html += f'<td class="number-cell">{tc_disp}</td>'
        html += f'<td class="number-cell">{tt_disp}</td>'
        html += render_progress_cell(cad['percent'], cad['tc'])
        html += f'</tr>'
        
        # CNC row
        cnc = cat_data.get('CNC', {'tc': 0, 'tt': 0, 'percent': 0})
        tc_disp = int(cnc['tc']) if cnc['tc'] > 0 else ''
        tt_disp = int(cnc['tt']) if cnc['tt'] > 0 else ''
        html += f'<tr>'
        html += f'<td class="category-cell" colspan="2">CNC</td>'
        html += f'<td class="number-cell">{tc_disp}</td>'
        html += f'<td class="number-cell">{tt_disp}</td>'
        html += render_progress_cell(cnc['percent'], cnc['tc'])
        html += f'</tr>'
        
        # VÁN row
        van = cat_data.get('VÁN', {'tc': 0, 'tt': 0, 'percent': 0})
        tc_disp = int(van['tc']) if van['tc'] > 0 else ''
        tt_disp = int(van['tt']) if van['tt'] > 0 else ''
        html += f'<tr>'
        html += f'<td class="category-cell" colspan="2">VÁN</td>'
        html += f'<td class="number-cell">{tc_disp}</td>'
        html += f'<td class="number-cell">{tt_disp}</td>'
        html += render_progress_cell(van['percent'], van['tc'])
        html += f'</tr>'
        
        # VẬT TƯ - 2 rows (Nhóm hàng, Số lượng)
        vt = cat_data.get('VẬT TƯ', {'tc': 0, 'tt': 0, 'percent': 0, 'nhom_hang_tc': 0, 'nhom_hang_tt': 0, 'nhom_percent': 0})
        # Row 1: Nhóm hàng (unique count)
        nhom_tc = int(vt.get('nhom_hang_tc', 0)) if vt.get('nhom_hang_tc', 0) > 0 else ''
        nhom_tt = int(vt.get('nhom_hang_tt', 0)) if vt.get('nhom_hang_tt', 0) > 0 else ''
        html += f'<tr>'
        html += f'<td class="category-cell" rowspan="2">VẬT TƯ</td>'
        html += f'<td class="sub-cell">Nhóm hàng</td>'
        html += f'<td class="number-cell">{nhom_tc}</td>'
        html += f'<td class="number-cell">{nhom_tt}</td>'
        html += render_progress_cell(vt.get('nhom_percent', 0), vt.get('nhom_hang_tc', 0))
        html += f'</tr>'
        # Row 2: Số lượng
        tc_disp = int(vt['tc']) if vt['tc'] > 0 else ''
        tt_disp = int(vt['tt']) if vt['tt'] > 0 else ''
        html += f'<tr>'
        html += f'<td class="sub-cell">Số lượng</td>'
        html += f'<td class="number-cell">{tc_disp}</td>'
        html += f'<td class="number-cell">{tt_disp}</td>'
        html += render_progress_cell(vt['percent'], vt['tc'])
        html += f'</tr>'
        
        # VẬT TƯ ƯU TIÊN - 2 rows (Nhóm hàng, Số lượng)
        vtut = cat_data.get('VẬT TƯ ƯU TIÊN', {'tc': 0, 'tt': 0, 'percent': 0, 'nhom_hang_tc': 0, 'nhom_hang_tt': 0, 'nhom_percent': 0})
        # Row 1: Nhóm hàng (unique count)
        nhom_tc = int(vtut.get('nhom_hang_tc', 0)) if vtut.get('nhom_hang_tc', 0) > 0 else ''
        nhom_tt = int(vtut.get('nhom_hang_tt', 0)) if vtut.get('nhom_hang_tt', 0) > 0 else ''
        html += f'<tr>'
        html += f'<td class="category-cell" rowspan="2">VẬT TƯ ƯU TIÊN</td>'
        html += f'<td class="sub-cell">Nhóm hàng</td>'
        html += f'<td class="number-cell">{nhom_tc}</td>'
        html += f'<td class="number-cell">{nhom_tt}</td>'
        html += render_progress_cell(vtut.get('nhom_percent', 0), vtut.get('nhom_hang_tc', 0))
        html += f'</tr>'
        # Row 2: Số lượng
        tc_disp = int(vtut['tc']) if vtut['tc'] > 0 else ''
        tt_disp = int(vtut['tt']) if vtut['tt'] > 0 else ''
        html += f'<tr>'
        html += f'<td class="sub-cell">Số lượng</td>'
        html += f'<td class="number-cell">{tc_disp}</td>'
        html += f'<td class="number-cell">{tt_disp}</td>'
        html += render_progress_cell(vtut['percent'], vtut['tc'])
        html += f'</tr>'
    
    html += "</tbody></table></body></html>"
    return html

def render_timeline_html(milestones):
    """Render timeline with alternating above/below milestones."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { margin: 0; padding: 20px 40px; background: #0f172a; }
        .timeline-wrapper {
            position: relative;
            height: 120px;
        }
        .timeline-bar {
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 3px;
            background: #0ea5e9;
            transform: translateY(-50%);
        }
        .milestones {
            display: flex;
            justify-content: space-between;
            position: relative;
            height: 100%;
            align-items: center;
        }
        .milestone {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .milestone-dot {
            width: 12px;
            height: 12px;
            background: #f97316;
            border-radius: 50%;
            position: relative;
            z-index: 2;
        }
        .milestone-above {
            position: absolute;
            bottom: 50%;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .milestone-below {
            position: absolute;
            top: 50%;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .milestone-line-up {
            width: 2px;
            height: 25px;
            background: #f97316;
        }
        .milestone-line-down {
            width: 2px;
            height: 25px;
            background: #f97316;
        }
        .milestone-info {
            font-size: 11px;
            color: #f97316;
            text-align: center;
            white-space: nowrap;
        }
        .milestone-date {
            font-weight: 700;
            font-size: 12px;
            margin-bottom: 2px;
        }
        .milestone-desc {
            color: #94a3b8;
            font-size: 10px;
        }
        .milestone-detail {
            color: #e2e8f0;
            font-size: 10px;
            line-height: 1.4;
        }
    </style>
    </head>
    <body>
    <div class="timeline-wrapper">
        <div class="timeline-bar"></div>
        <div class="milestones">
    """
    
    for i, m in enumerate(milestones):
        is_above = (i % 2 == 0)  # Alternating: even=above, odd=below
        
        # Build info block with all details
        info_block = f"""
            <div class="milestone-info">
                <div class="milestone-date">{m['date']}</div>
                <div class="milestone-desc">{m['desc']}</div>
                <div class="milestone-detail">Shop duyệt: {m['shop']}</div>
                <div class="milestone-detail">Ván: {m['van']}</div>
                <div class="milestone-detail">Sản xuất: {m['sx']}</div>
                <div class="milestone-detail">Vật tư: {m['vt']}</div>
            </div>
        """
        
        if is_above:
            html += f"""
            <div class="milestone">
                <div class="milestone-above">
                    {info_block}
                    <div class="milestone-line-up"></div>
                </div>
                <div class="milestone-dot"></div>
            </div>
            """
        else:
            html += f"""
            <div class="milestone">
                <div class="milestone-dot"></div>
                <div class="milestone-below">
                    <div class="milestone-line-down"></div>
                    {info_block}
                </div>
            </div>
            """
    
    html += "</div></div></body></html>"
    return html

def render_matrix_html(matrix_df):
    """Render matrix table in grid layout with Delta-based icons and colors."""
    if matrix_df.empty:
        return "<p>Không có dữ liệu Matrix.</p>"
    
    # Get list of product codes
    products = matrix_df.index.tolist()
    total = len(products)
    
    # Split into groups of ~17 items
    items_per_group = 17
    num_groups = math.ceil(total / items_per_group)
    
    # Column headers (vertical text)
    headers = ['Mã SP', 'CAD', 'ĐẶT HÀNG', 'CNC', 'VẬT TƯ ƯU TIÊN', 'VẬT TƯ']
    
    def get_cell_style(delta):
        """Returns (icon, bg_color) based on Delta value."""
        if delta == 0:
            return ('✔', '#1E88E5')  # Tích trắng + nền xanh biển
        elif delta > 0:
            return ('🔼', '#FF9800')  # Vàng - Đang thực hiện
        else:
            return ('❌', '#F44336')  # Đỏ - Sai lệch
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { margin: 0; padding: 10px; background: transparent; }
        .matrix-container {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .matrix-group {
            border: 1px solid #334155;
        }
        .matrix-table {
            border-collapse: collapse;
            font-size: 11px;
        }
        .matrix-table th {
            background: #1e3a5f;
            color: #e2e8f0;
            padding: 4px 2px;
            border: 1px solid #334155;
            font-weight: 600;
            text-align: center;
            height: 80px;
            width: 35px;
        }
        .matrix-table th .vertical-text {
            writing-mode: vertical-rl;
            text-orientation: mixed;
            transform: rotate(180deg);
            white-space: nowrap;
        }
        .matrix-table th:first-child {
            width: 60px;
        }
        .matrix-table td {
            padding: 3px 4px;
            border: 1px solid #334155;
            color: white;
            background: #0f172a;
            text-align: center;
            font-size: 12px;
        }
        .matrix-table td:first-child {
            text-align: left;
            background: #1e293b;
            color: #e2e8f0;
            font-weight: 500;
        }
        .cell-empty {
            background: linear-gradient(to top right, transparent calc(50% - 1px), #475569, transparent calc(50% + 1px)),
                        linear-gradient(to top left, transparent calc(50% - 1px), #475569, transparent calc(50% + 1px)) !important;
        }
    </style>
    </head>
    <body>
    <div class="matrix-container">
    """
    
    for g in range(num_groups):
        start_idx = g * items_per_group
        end_idx = min((g + 1) * items_per_group, total)
        group_products = products[start_idx:end_idx]
        
        html += '<div class="matrix-group"><table class="matrix-table">'
        
        # Header row with vertical text
        html += '<thead><tr>'
        for h in headers:
            if h == 'Mã SP':
                html += f'<th>{h}</th>'
            else:
                html += f'<th><div class="vertical-text">{h}</div></th>'
        html += '</tr></thead><tbody>'
        
        # Data rows
        for prod in group_products:
            row_data = matrix_df.loc[prod] if prod in matrix_df.index else {}
            
            # Calculate Delta and get icon/color for CAD
            cad_tc = row_data.get('CAD_TC', 0) if 'CAD_TC' in row_data else 0
            cad_tt = row_data.get('CAD_TT', 0) if 'CAD_TT' in row_data else 0
            cad_delta = cad_tc - cad_tt
            cad_icon, cad_color = get_cell_style(cad_delta) if cad_tc > 0 else ('', '#0f172a')
            
            # Calculate Delta for CNC
            cnc_tc = row_data.get('CNC_TC', 0) if 'CNC_TC' in row_data else 0
            cnc_tt = row_data.get('CNC_TT', 0) if 'CNC_TT' in row_data else 0
            cnc_delta = cnc_tc - cnc_tt
            cnc_icon, cnc_color = get_cell_style(cnc_delta) if cnc_tc > 0 else ('', '#0f172a')
            
            # Empty cell with X mark style
            empty_cell = '<td class="cell-empty"></td>'
            
            html += f'<tr>'
            html += f'<td>{prod}</td>'
            
            # CAD cell with icon and color
            if cad_tc > 0:
                html += f'<td style="background:{cad_color};">{cad_icon}</td>'
            else:
                html += empty_cell
            
            # ĐẶT HÀNG (placeholder - marked as empty)
            html += empty_cell
            
            # CNC cell with icon and color
            if cnc_tc > 0:
                html += f'<td style="background:{cnc_color};">{cnc_icon}</td>'
            else:
                html += empty_cell
            
            # VẬT TƯ ƯU TIÊN
            vt_ut_tc = row_data.get('VAT_TU_UU_TIEN_TC', 0) if 'VAT_TU_UU_TIEN_TC' in row_data else 0
            vt_ut_tt = row_data.get('VAT_TU_UU_TIEN_TT', 0) if 'VAT_TU_UU_TIEN_TT' in row_data else 0
            vt_ut_delta = vt_ut_tc - vt_ut_tt
            
            if vt_ut_tc > 0:
                icon, color = get_cell_style(vt_ut_delta)
                html += f'<td style="background:{color};">{icon}</td>'
            else:
                html += empty_cell

            # VẬT TƯ (Normal)
            vt_tc = row_data.get('VAT_TU_TC', 0) if 'VAT_TU_TC' in row_data else 0
            vt_tt = row_data.get('VAT_TU_TT', 0) if 'VAT_TU_TT' in row_data else 0
            vt_delta = vt_tc - vt_tt
            
            if vt_tc > 0:
                icon, color = get_cell_style(vt_delta)
                html += f'<td style="background:{color};">{icon}</td>'
            else:
                html += empty_cell
            html += '</tr>'
        
        html += '</tbody></table></div>'
    
    html += "</div></body></html>"
    return html

# ============================================================
# SESSION STATE
# ============================================================
if 'master_data' not in st.session_state:
    st.session_state.master_data = None
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = None
if 'selected_contract' not in st.session_state:
    st.session_state.selected_contract = None
if 'drive_root_id' not in st.session_state:
    st.session_state.drive_root_id = ''
if 'local_root_path' not in st.session_state:
    st.session_state.local_root_path = DEFAULT_ROOT_PATH
if 'data_source' not in st.session_state:
    st.session_state.data_source = 'Google Drive'
if 'years_map' not in st.session_state:
    st.session_state.years_map = {}
if 'contracts_map' not in st.session_state:
    st.session_state.contracts_map = {}
# Smart Cache: Store modification timestamps
if 'cache_timestamps' not in st.session_state:
    st.session_state.cache_timestamps = {}  # {year: {contract_id: modifiedTime}}
if 'cache_loaded_year' not in st.session_state:
    st.session_state.cache_loaded_year = None
if 'details_cache' not in st.session_state:
    st.session_state.details_cache = {}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🏭 Quản lý Sản xuất")
    
    # Source Toggle
    source = st.radio("Nguồn dữ liệu", ["Google Drive", "Local HDD (Offline)"], 
                      index=0 if st.session_state.data_source == 'Google Drive' else 1)
    st.session_state.data_source = source
    st.markdown("---")
    
    # GOOGLE DRIVE MODE
    if source == 'Google Drive':
        # Hardcoded Year Shortcuts
        YEAR_FOLDERS = {
            '2026': '1hn-nFm56a3X24qs3WbweJfx6BqJ9ggr6',
            '2025': '1YoRBhoWDXMB4-byVtyqHHNKM1PVKbptd',
        }
        
        years_list = list(YEAR_FOLDERS.keys())
        selected_year = st.selectbox("📅 Chọn Năm", years_list, index=0)
        st.session_state.selected_year = selected_year
        st.session_state.drive_root_id = YEAR_FOLDERS[selected_year]
        st.session_state.years_map = YEAR_FOLDERS
        
        # Auto-load from SHARED cache on page load
        year_folder_id = YEAR_FOLDERS[selected_year]
        if st.session_state.master_data is None:
            shared_data, _, details = load_shared_cache(str(selected_year), year_folder_id)
            if shared_data:
                st.session_state.master_data = shared_data
                if details:
                    st.session_state.details_cache = details
                st.toast(f"⚡ Đã tải dữ liệu năm {selected_year} từ cache!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Tải dữ liệu", use_container_width=True):
                with st.spinner("Đang kiểm tra và tải..."):
                    st.session_state.master_data = load_all_contracts_data_logic(selected_year, YEAR_FOLDERS)
                    st.success(f"✅ Đã tải năm {selected_year}!")
                    st.rerun()
        with col2:
            if st.button("🔃 Làm mới", use_container_width=True, help="Bỏ qua cache, tải lại toàn bộ"):
                with st.spinner("Đang tải lại toàn bộ..."):
                    st.session_state.master_data = load_all_contracts_data_logic(selected_year, YEAR_FOLDERS, force_reload=True)
                    st.success(f"✅ Đã tải mới năm {selected_year}!")
                    st.rerun()
        
        st.markdown("---")
        
        if st.session_state.master_data:
            year_id = YEAR_FOLDERS.get(str(selected_year))
            c_map, c_list = get_contracts_for_year_drive(year_id)
            st.session_state.contracts_map = c_map
            
            st.markdown("### 📁 Xem chi tiết")
            selected_contract = st.selectbox("Chọn Hợp đồng", ["-- Chọn --"] + c_list)
            if selected_contract != "-- Chọn --":
                st.session_state.selected_contract = selected_contract
            else:
                st.session_state.selected_contract = None
            
    # LOCAL HDD MODE
    else:
        local_path = st.text_input("Đường dẫn Local", value=st.session_state.local_root_path)
        st.session_state.local_root_path = local_path
        
        years = get_available_years_local(local_path)
        if years:
            selected_year = st.selectbox("📅 Chọn Năm", years, index=0)
            st.session_state.selected_year = selected_year
            
            if st.button("🔄 Tải tất cả dự án (Local)", use_container_width=True):
                with st.spinner("Đang quét ổ cứng..."):
                    st.session_state.master_data = load_all_contracts_data_local(local_path, selected_year)
                    st.success(f"✅ Đã tải năm {selected_year}!")
                    st.rerun()
            
            st.markdown("---")
            
            if st.session_state.master_data:
                contracts = get_contracts_for_year_local(local_path, selected_year)
                st.markdown("### 📁 Xem chi tiết")
                selected_contract = st.selectbox("Chọn Hợp đồng", ["-- Chọn --"] + contracts)
                if selected_contract != "-- Chọn --":
                    st.session_state.selected_contract = selected_contract
                else:
                    st.session_state.selected_contract = None
        else:
            # DEBUG: Show what's in the folder
            if os.path.exists(local_path):
                try:
                    all_items = os.listdir(local_path)
                    dirs_only = [d for d in all_items if os.path.isdir(os.path.join(local_path, d))]
                    st.warning(f"⚠️ Đường dẫn tồn tại nhưng không tìm thấy năm. Các thư mục hiện có: {dirs_only[:10]}")
                except Exception as e:
                    st.error(f"Lỗi liệt kê thư mục: {e}")
            else:
                st.error(f"❌ Đường dẫn không tồn tại: `{local_path}`")

# ============================================================
# MAIN AREA
# ============================================================
st.markdown("### 📊 Tổng quan")

if st.session_state.master_data:
    html = render_master_table_html(st.session_state.master_data)
    # New structure: 7 rows per contract (CAD, CNC, VÁN, VẬT TƯx2, VẬT TƯ ƯU TIÊNx2)
    num_contracts = len(set([d['contract'] for d in st.session_state.master_data]))
    height = min(max(300, num_contracts * 7 * 28 + 60), 800)
    components.html(html, height=height, scrolling=True)
else:
    st.info("👈 Chọn Năm ở Sidebar và nhấn **Tải tất cả dự án** để xem bảng tổng hợp.")

# ============================================================
# TIMELINE SECTION
# ============================================================
# ============================================================
# TIMELINE & MATRIX SECTION (RENDER PER CONTRACT)
# ============================================================

def render_matrix_grids_html(matrix_df, details_map):
    """Render matrix using CSS Grid - 4 columns, click expands full-width detail row inline."""
    if matrix_df.empty:
        return "<p>Không có dữ liệu Matrix.</p>"
    
    products = matrix_df.index.tolist()
    total = len(products)
    items_per_group = 25
    num_groups = math.ceil(total / items_per_group)
    
    # Organize products into groups (columns)
    groups = []
    for g in range(num_groups):
        start_idx = g * items_per_group
        end_idx = min((g + 1) * items_per_group, total)
        groups.append(products[start_idx:end_idx])
    
    # Find max rows needed
    max_rows = max(len(g) for g in groups) if groups else 0
    
    headers = ['Mã SP', 'Tên SP', 'CAD', 'ĐẶT HÀNG', 'CNC', 'Vật tư ưu tiên', 'Vật tư']
    
    def get_cell_style(delta):
        # delta = TC - TT
        if delta == 0: return ('✔', '#1E88E5')   # TT = TC: Complete (blue)
        elif delta < 0: return ('➚', '#FFEB3B')  # TT > TC: Exceeded (yellow)
        else: return ('✖', '#F44336')            # TT < TC: Incomplete (red)
    
    # Prepare details JSON for JavaScript
    import json
    details_json = json.dumps(details_map, ensure_ascii=False, default=str)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ box-sizing: border-box; font-family: Arial, sans-serif; }}
        body {{ margin: 0; padding: 10px; background: transparent; }}
        
        .matrix-grid {{
            display: grid;
            grid-template-columns: repeat({num_groups}, 1fr);
            gap: 10px;
        }}
        
        .grid-column {{
            display: flex;
            flex-direction: column;
        }}
        
        .column-header {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            align-items: center;
            background: #1e3a5f;
            border: 1px solid #334155;
        }}
        
        .column-header span {{
            color: #e2e8f0;
            font-size: 10px;
            font-weight: 600;
            text-align: center;
            padding: 3px 2px;
            border-right: 1px solid #334155;
        }}
        
        .column-header span:nth-child(n+1) {{ text-align: center; }}
        
        .column-header span:nth-child(n+3) {{
            writing-mode: vertical-rl;
            text-orientation: mixed;
            transform: rotate(180deg);
            height: 70px;
        }}
        
        .product-row {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            border: 1px solid #334155;
            align-items: stretch; /* Ensure cells stretch to full height */
            border-top: none;
            background: #0f172a;
            color: #cbd5e1;
            font-size: 11px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .product-row:hover {{
            background: #334155;
        }}
        
        .product-row.selected {{
            background: #3b82f6 !important;
            color: white !important;
        }}
        
        .product-row span {{
            padding: 4px 2px;
            display: flex; /* Use flexbox for centering */
            align-items: center;
            justify-content: center;
            border-right: 1px solid #334155;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }}
        
        .detail-row {{
            grid-column: 1 / -1; /* Span all columns */
            background: #1e293b;
            border: 1px solid #475569;
            margin-bottom: 10px;
            padding: 10px;
            display: none; /* Hidden by default */
        }}
        
        .detail-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            color: #e2e8f0;
        }}
        
        .detail-table th {{
            background: #334155;
            padding: 5px;
            text-align: left;
            border: 1px solid #475569;
        }}
        
        .detail-table td {{
            padding: 5px;
            border: 1px solid #475569;
        }}

        .status-ok {{ background-color: #4CAF50 !important; color: white; text-align: center; font-weight: 600; }}
        .status-missing {{ background-color: #F44336 !important; color: white; text-align: center; font-weight: 600; }}
        .status-extra {{ background-color: #FFEB3B !important; color: #333; text-align: center; font-weight: 600; }}
        
        .empty-cell {{
            visibility: hidden;
            height: 22px;
        }}
    </style>
    <script>
        var allDetails = {details_json};
        var selectedRow = null;
        var activeDetailRow = null;
        
        function showDetail(productCode, rowElement, detailRowId) {{
            // Deselect previous
            if (selectedRow) {{
                selectedRow.classList.remove('selected');
            }}
            if (activeDetailRow) {{
                activeDetailRow.style.display = 'none';
            }}
            
            // Toggle off if clicking same row
            if (selectedRow === rowElement) {{
                selectedRow = null;
                activeDetailRow = null;
                return;
            }}
            
            // Select new
            rowElement.classList.add('selected');
            selectedRow = rowElement;
            
            var detailRow = document.getElementById(detailRowId);
            detailRow.style.display = 'block';
            activeDetailRow = detailRow;
            
            var tbody = detailRow.querySelector('.detail-tbody');
            var details = allDetails[productCode] || [];
            
            tbody.innerHTML = '';
            
            if (details.length === 0) {{
                tbody.innerHTML = '<tr><td class="product-cell">' + productCode + '</td><td colspan="9" style="text-align:center; color:#94a3b8;">Chưa có dữ liệu chi tiết</td></tr>';
            }} else {{
                var cadItems = details.filter(function(d) {{ return d.category === 'CAD'; }});
                
                var totalRows = details.length;
                 
                 details.forEach(function(d, i) {{
                     var row = '<tr>';
                     if (i===0) {{
                         row += '<td rowspan="' + details.length + '">' + productCode + '</td>';
                         row += '<td rowspan="' + details.length + '">' + (d.product_name || '') + '</td>';
                     }}
                     row += '<td>' + (d.item_name || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.quantity || 0) + '</td>';
                     row += '<td style="text-align:center;">' + (d.remaining || 0) + '</td>';
                     row += '<td style="text-align:center;">' + (d.unit || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.creation_date || d.date || '') + '</td>';
                     
                     var st = d.status || '';
                     var stClass = '';
                     var stIcon = '';
                     
                     if (st === 'Hoàn thành' || st === 'OK' || st === 'Đủ') {{ stClass = 'status-done'; stIcon = '✔ '; }}
                     else if (st === 'Đang làm' || st === 'Thiếu') {{ stClass = 'status-missing'; stIcon = '⏳ '; }}
                     else if (st === 'Phát sinh' || st === 'Vượt KH' || st === 'Dư') {{ stClass = 'status-extra'; stIcon = '⚠ '; }}
                     
                     row += '<td style="text-align:center;">' + (d.date || d.creation_date || '') + '</td>';
                     row += '<td class="' + stClass + '">' + stIcon + st + '</td>'; 
                     row += '<td>' + (d.note || '') + '</td>';
                     row += '</tr>';
                     tbody.innerHTML += row;
                 }});
            }}
        }}
    </script>
    </head>
    <body>
    """
    
    for row_idx in range(max_rows):
        # Start a visual row container
        html += '<div class="matrix-grid">'
        
        # Add header if first row
        if row_idx == 0:
            for g in range(num_groups):
                html += '<div class="column-header">'
                for h in headers:
                    html += f'<span>{h}</span>'
                html += '</div>'
            html += '</div><div class="matrix-grid">'
        
        # Add product cells for each group
        for g in range(num_groups):
            if row_idx < len(groups[g]):
                prod = groups[g][row_idx]
                row_data = matrix_df.loc[prod] if prod in matrix_df.index else {}
                
                def get_cell(tc_key, tt_key):
                    tc = row_data.get(tc_key, 0)
                    tt = row_data.get(tt_key, 0)
                    if tc > 0:
                        icon, color = get_cell_style(tc - tt)
                        return f'<span style="background:{color};">{icon}</span>'
                    return '<span class="cell-empty"></span>'
                
                safe_prod = prod.replace("'", "\\'").replace('"', '\\"')
                detail_row_id = f'detail_row_{row_idx}'
                
                html += f'<div class="grid-column"><div class="product-row" onclick="showDetail(\'{safe_prod}\', this, \'{detail_row_id}\')">'
                html += f'<span>{prod}</span>'
                html += f'<span style="text-align:left !important; padding-left:4px; font-weight:normal;" title="{row_data.get("TEN_SP", "")}">{row_data.get("TEN_SP", "")}</span>'
                html += get_cell('CAD_TC', 'CAD_TT')
                html += get_cell('DAT_HANG_TC', 'DAT_HANG_TT')
                html += get_cell('CNC_TC', 'CNC_TT')
                html += get_cell('VAT_TU_UU_TIEN_TC', 'VAT_TU_UU_TIEN_TT')
                html += get_cell('VAT_TU_TC', 'VAT_TU_TT')
                html += '</div></div>'
            else:
                # Empty placeholder for alignment
                html += '<div class="grid-column"><div class="product-row empty-cell"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div></div>'
        
        html += '</div>'  # End matrix-grid row
        
        # Add detail row placeholder (full-width, hidden by default)
        detail_row_id = f'detail_row_{row_idx}'
        html += f'''
        <div id="{detail_row_id}" class="detail-row">
            <table class="detail-table">
                <thead>
                    <tr>
                        <th style="width:90px;">Mã SP</th>
                        <th>TÊN SP</th>
                        <th>TÊN HÀNG</th>
                        <th style="width:60px;">SỐ LƯỢNG</th>
                        <th style="width:50px;">TỒN</th>
                        <th style="width:55px;">ĐƠN VỊ</th>
                        <th style="width:100px;">NGÀY LẬP DS</th>
                        <th style="width:100px;">HOÀN THÀNH</th>
                        <th style="width:85px;">TRẠNG THÁI</th>
                        <th style="width:100px;">GHI CHÚ</th>
                    </tr>
                </thead>
                <tbody class="detail-tbody"></tbody>
            </table>
        </div>
        '''
    
    html += '</body></html>'
    return html

# 1. Determine which contracts to show
contracts_to_render = []

if st.session_state.selected_contract:
    contracts_to_render = [st.session_state.selected_contract]
else:
    # Show ALL contracts (sorted naturally)
    if st.session_state.contracts_map:
        contracts = list(st.session_state.contracts_map.keys())
        contracts_to_render = sorted(contracts, key=natural_sort_key)
    else:
        st.info("Chưa tải danh sách hợp đồng. Vui lòng chọn Năm và tải dữ liệu.")

# 2. Iterate and Render
if contracts_to_render:
    # Pre-load details cache if available to avoid repeated lookups
    details_cache = st.session_state.get('details_cache', {})
    master_data = st.session_state.get('master_data', [])
    
    # Create helper map for Master Data stats
    stats_map = {}
    if master_data:
        for row in master_data:
            if 'contract' in row:
                stats_map[row['contract']] = row

    if not details_cache and len(contracts_to_render) > 1:
        st.warning("⚠️ Dữ liệu chi tiết chưa được tải đầy đủ. Vui lòng nhấn **'Tải dữ liệu'** để xem danh sách Matrix đầy đủ.")

    for contract_name in contracts_to_render:
        
        # Determine contract ID and Files
        contract_files = []
        if st.session_state.data_source == 'Google Drive':
            c_id = st.session_state.contracts_map.get(contract_name)
            # Try Cache First
            if c_id and c_id in details_cache:
                cached_files = details_cache[c_id]
                import base64
                for f in cached_files:
                    new_f = f.copy()
                    content = f.get('content')
                    if isinstance(content, str):
                        try:
                            new_f['content'] = base64.b64decode(content)
                        except:
                            pass
                    contract_files.append(new_f)
            # Fallback to Drive Load (only if single contract selected to avoid mass API hit)
            elif c_id and len(contracts_to_render) == 1:
                contract_files = load_data_from_drive(c_id)
        else:
            # Local Mode
            c_path = os.path.join(st.session_state.local_root_path, str(st.session_state.selected_year), contract_name)
            contract_files = scan_project_files(c_path)
            
        # HEADER
        st.markdown(f"### 🏗️ {contract_name}")
        
        
        # --- TIMELINE / STATS ---
        aggs = calculate_aggregates(contract_files) if contract_files else {}
        # Falls back to master_data cache if files missing
        if not contract_files and contract_name in stats_map:
            row = stats_map[contract_name]
            def parse_stat(val):
                if isinstance(val, str) and '/' in val:
                    parts = val.split('/')
                    return {'TT': int(parts[0]), 'TC': int(parts[1])}
                return {'TC': 0, 'TT': 0}
            
            cad_stats = parse_stat(row.get('CAD', '0/0'))
            cnc_stats = parse_stat(row.get('CNC', '0/0'))
            van_stats = parse_stat(row.get('VÁN', '0/0'))
            vt_stats = parse_stat(row.get('VẬT TƯ', '0/0'))
        else:
             cad_stats = aggs.get('CAD', {'TC': 0, 'TT': 0})
             cnc_stats = aggs.get('CNC', {'TC': 0, 'TT': 0})
             van_stats = aggs.get('VAN', {'TC': 0, 'TT': 0})
             vt_stats = aggs.get('VAT_TU', {'TC': 0, 'TT': 0})

        # Render Stats Bar
        st.markdown(f"""
        <div style="background: #1e293b; padding: 8px 16px; border-radius: 8px; margin: 8px 0; font-size: 13px; color: #cbd5e1; font-family: Arial, sans-serif;">
            <span style="margin-right: 24px;"><b>Shop duyệt:</b> {int(cad_stats['TT'])}/{int(cad_stats['TC'])}</span>
            <span style="margin-right: 24px;"><b>Ván:</b> {int(van_stats['TT'])}/{int(van_stats['TC'])}</span>
            <span style="margin-right: 24px;"><b>Sản xuất:</b> {int(cnc_stats['TT'])}/{int(cnc_stats['TC'])}</span>
            <span><b>Vật tư:</b> {int(vt_stats['TT'])}/{int(vt_stats['TC'])}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Render Timeline Chart (Restored)
        # Using simple sample milestones for now, as real milestone logic from files is complex
        # Ideally this should come from a project_plan.xlsx or similar if it exists
        sample_milestones = [
            {"date": "...", "desc": "Bắt đầu", "shop": "...", "van": "...", "sx": "...", "vt": "..."},
        ]
        # Only render if we have some data or specific logic
        timeline_html = render_timeline_html(sample_milestones)
        # components.html(timeline_html, height=200) # Commented out as it takes too much space, just showing Stats Bar is cleaner per user preference?
        # User requested "bị mất bảng timeline", so I MUST uncomment it.
        components.html(timeline_html, height=180) 

        # Display Matrix
        if contract_files:
            matrix = build_matrix_table(contract_files)
            if not matrix.empty:
                # Load Details for this contract
                from src.core.calculator import get_all_product_details
                details_map = get_all_product_details(contract_files)
                
                # DEBUG: Show sample details_map data
                with st.expander("🔍 DEBUG: Chi tiết dữ liệu (click để xem)", expanded=False):
                    if details_map:
                        sample_key = list(details_map.keys())[0] if details_map else None
                        if sample_key:
                            st.write(f"**Sample Key:** `{sample_key}`")
                            st.json(details_map.get(sample_key, []))
                    else:
                        st.warning("details_map is empty!")
                
                # Render HTML
                html_content = render_matrix_grids_html(matrix, details_map)
                
                # Calculate height: Collapsed vs Expanded
                # Using a tighter bound: 150(Header+Stats) + Rows*30 + Buffer
                # We can't know if user expands, but 400 was too much.
                # Let's drop buffer to 100, and rely on user scrolling if they expand A LOT.
                total_height = 100 + (len(matrix) * 32) + 150 
                components.html(html_content, height=total_height, scrolling=True)
            else:
                 st.info(f"ℹ️ Không có dữ liệu Matrix cho {contract_name}")
        else:
             if len(contracts_to_render) == 1:
                 st.warning("⚠️ Không tìm thấy dữ liệu file.")
             else:
                 st.caption("⚠️ Chưa tải chi tiết. Vui lòng bấm 'Tải dữ liệu'.")
        
        st.markdown("---") 

# Function definition must remain outside loop
def render_matrix_grids_html(matrix_df, details_map):
    """Render matrix using CSS Grid - 4 columns, click expands full-width detail row inline."""
    if matrix_df.empty:
        return "<p>Không có dữ liệu Matrix.</p>"
    
    products = matrix_df.index.tolist()
    total = len(products)
    items_per_group = 25
    num_groups = math.ceil(total / items_per_group)
    
    # Organize products into groups (columns)
    groups = []
    for g in range(num_groups):
        start_idx = g * items_per_group
        end_idx = min((g + 1) * items_per_group, total)
        groups.append(products[start_idx:end_idx])
    
    # Find max rows needed
    max_rows = max(len(g) for g in groups) if groups else 0
    
    headers = ['Mã SP', 'Tên SP', 'CAD', 'ĐẶT HÀNG', 'CNC', 'Vật tư ưu tiên', 'Vật tư']
    
    def get_cell_style(delta):
        # delta = TC - TT
        if delta == 0: return ('✔', '#1E88E5')   # TT = TC: Complete (blue)
        elif delta < 0: return ('➚', '#FFEB3B')  # TT > TC: Exceeded (yellow)
        else: return ('✖', '#F44336')            # TT < TC: Incomplete (red)
    
    # Prepare details JSON for JavaScript
    import json
    details_json = json.dumps(details_map, ensure_ascii=False, default=str)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ box-sizing: border-box; font-family: Arial, sans-serif; }}
        body {{ margin: 0; padding: 10px; background: transparent; }}
        
        .matrix-grid {{
            display: grid;
            grid-template-columns: repeat({num_groups}, 1fr);
            gap: 10px;
        }}
        
        .grid-column {{
            display: flex;
            flex-direction: column;
        }}
        
        .column-header {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            align-items: center;
            background: #1e3a5f;
            border: 1px solid #334155;
        }}
        
        .column-header span {{
            color: #e2e8f0;
            font-size: 10px;
            font-weight: 600;
            text-align: center;
            padding: 3px 2px;
            border-right: 1px solid #334155;
        }}
        
        .column-header span:nth-child(n+1) {{ text-align: center; }}
        
        .column-header span:nth-child(n+3) {{
            writing-mode: vertical-rl;
            text-orientation: mixed;
            transform: rotate(180deg);
            height: 70px;
        }}
        
        .product-row {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            border: 1px solid #334155;
            align-items: stretch; /* Ensure cells stretch to full height */
            border-top: none;
            background: #0f172a;
            color: #cbd5e1;
            font-size: 11px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .product-row:hover {{
            background: #334155;
        }}
        
        .product-row.selected {{
            background: #3b82f6 !important;
            color: white !important;
        }}
        
        .product-row span {{
            padding: 4px 2px;
            display: flex; /* Use flexbox for centering */
            align-items: center;
            justify-content: center;
            border-right: 1px solid #334155;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }}
        
        .detail-row {{
            grid-column: 1 / -1; /* Span all columns */
            background: #1e293b;
            border: 1px solid #475569;
            margin-bottom: 10px;
            padding: 10px;
            display: none; /* Hidden by default */
        }}
        
        .detail-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            color: #e2e8f0;
        }}
        
        .detail-table th {{
            background: #334155;
            padding: 5px;
            text-align: left;
            border: 1px solid #475569;
        }}
        
        .detail-table td {{
            padding: 5px;
            border: 1px solid #475569;
        }}

        .status-ok {{ background-color: #4CAF50 !important; color: white; text-align: center; font-weight: 600; }}
        .status-missing {{ background-color: #F44336 !important; color: white; text-align: center; font-weight: 600; }}
        .status-extra {{ background-color: #FFEB3B !important; color: #333; text-align: center; font-weight: 600; }}
        
        .empty-cell {{
            visibility: hidden;
            height: 22px;
        }}
    </style>
    <script>
        var allDetails = {details_json};
        var selectedRow = null;
        var activeDetailRow = null;
        
        function showDetail(productCode, rowElement, detailRowId) {{
            // Deselect previous
            if (selectedRow) {{
                selectedRow.classList.remove('selected');
            }}
            if (activeDetailRow) {{
                activeDetailRow.style.display = 'none';
            }}
            
            // Toggle off if clicking same row
            if (selectedRow === rowElement) {{
                selectedRow = null;
                activeDetailRow = null;
                return;
            }}
            
            // Select new
            rowElement.classList.add('selected');
            selectedRow = rowElement;
            
            var detailRow = document.getElementById(detailRowId);
            detailRow.style.display = 'block';
            activeDetailRow = detailRow;
            
            var tbody = detailRow.querySelector('.detail-tbody');
            var details = allDetails[productCode] || [];
            
            tbody.innerHTML = '';
            
            if (details.length === 0) {{
                tbody.innerHTML = '<tr><td class="product-cell">' + productCode + '</td><td colspan="9" style="text-align:center; color:#94a3b8;">Chưa có dữ liệu chi tiết</td></tr>';
            }} else {{
                var cadItems = details.filter(function(d) {{ return d.category === 'CAD'; }});
                
                var totalRows = details.length;
                 
                 details.forEach(function(d, i) {{
                     var row = '<tr>';
                     if (i===0) {{
                         row += '<td rowspan="' + details.length + '">' + productCode + '</td>';
                         row += '<td rowspan="' + details.length + '">' + (d.product_name || '') + '</td>';
                     }}
                     row += '<td>' + (d.item_name || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.quantity || 0) + '</td>';
                     row += '<td style="text-align:center;">' + (d.remaining || 0) + '</td>';
                     row += '<td style="text-align:center;">' + (d.unit || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.creation_date || d.date || '') + '</td>';
                     
                     var st = d.status || '';
                     var stClass = '';
                     var stIcon = '';
                     
                     if (st === 'Hoàn thành' || st === 'OK' || st === 'Đủ') {{ stClass = 'status-done'; stIcon = '✔ '; }}
                     else if (st === 'Đang làm' || st === 'Thiếu') {{ stClass = 'status-missing'; stIcon = '⏳ '; }}
                     else if (st === 'Phát sinh' || st === 'Vượt KH' || st === 'Dư') {{ stClass = 'status-extra'; stIcon = '⚠ '; }}
                     
                     row += '<td style="text-align:center;">' + (d.date || d.creation_date || '') + '</td>';
                     row += '<td class="' + stClass + '">' + stIcon + st + '</td>'; 
                     row += '<td>' + (d.note || '') + '</td>';
                     row += '</tr>';
                     tbody.innerHTML += row;
                 }});
            }}
        }}
    </script>
    </head>
    <body>
    """
    
    for row_idx in range(max_rows):
        # Start a visual row container
        html += '<div class="matrix-grid">'
        
        # Add header if first row
        if row_idx == 0:
            for g in range(num_groups):
                html += '<div class="column-header">'
                for h in headers:
                    html += f'<span>{h}</span>'
                html += '</div>'
            html += '</div><div class="matrix-grid">'
        
        # Add product cells for each group
        for g in range(num_groups):
            if row_idx < len(groups[g]):
                prod = groups[g][row_idx]
                row_data = matrix_df.loc[prod] if prod in matrix_df.index else {}
                
                def get_cell(tc_key, tt_key):
                    tc = row_data.get(tc_key, 0)
                    tt = row_data.get(tt_key, 0)
                    if tc > 0:
                        icon, color = get_cell_style(tc - tt)
                        return f'<span style="background:{color};">{icon}</span>'
                    return '<span class="cell-empty"></span>'
                
                safe_prod = prod.replace("'", "\\'").replace('"', '\\"')
                detail_row_id = f'detail_row_{row_idx}'
                
                html += f'<div class="grid-column"><div class="product-row" onclick="showDetail(\'{safe_prod}\', this, \'{detail_row_id}\')">'
                html += f'<span>{prod}</span>'
                html += f'<span style="text-align:left !important; padding-left:4px; font-weight:normal;" title="{row_data.get("TEN_SP", "")}">{row_data.get("TEN_SP", "")}</span>'
                html += get_cell('CAD_TC', 'CAD_TT')
                html += get_cell('DAT_HANG_TC', 'DAT_HANG_TT')
                html += get_cell('CNC_TC', 'CNC_TT')
                html += get_cell('VAT_TU_UU_TIEN_TC', 'VAT_TU_UU_TIEN_TT')
                html += get_cell('VAT_TU_TC', 'VAT_TU_TT')
                html += '</div></div>'
            else:
                # Empty placeholder for alignment
                html += '<div class="grid-column"><div class="product-row empty-cell"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div></div>'
        
        html += '</div>'  # End matrix-grid row
        
        # Add detail row placeholder (full-width, hidden by default)
        detail_row_id = f'detail_row_{row_idx}'
        html += f'''
        <div id="{detail_row_id}" class="detail-row">
            <table class="detail-table">
                <thead>
                    <tr>
                        <th style="width:90px;">Mã SP</th>
                        <th>TÊN SP</th>
                        <th>TÊN HÀNG</th>
                        <th style="width:60px;">SỐ LƯỢNG</th>
                        <th style="width:50px;">TỒN</th>
                        <th style="width:55px;">ĐƠN VỊ</th>
                        <th style="width:100px;">NGÀY LẬP DS</th>
                        <th style="width:100px;">HOÀN THÀNH</th>
                        <th style="width:85px;">TRẠNG THÁI</th>
                        <th style="width:100px;">GHI CHÚ</th>
                    </tr>
                </thead>
                <tbody class="detail-tbody"></tbody>
            </table>
        </div>
        '''
    
    html += '</body></html>'
    return html

def render_matrix_grids_html(matrix_df, details_map):
    """Render matrix using CSS Grid - 4 columns, click expands full-width detail row inline."""
    if matrix_df.empty:
        return "<p>Không có dữ liệu Matrix.</p>"
    
    products = matrix_df.index.tolist()
    total = len(products)
    items_per_group = 25
    num_groups = math.ceil(total / items_per_group)
    
    # Organize products into groups (columns)
    groups = []
    for g in range(num_groups):
        start_idx = g * items_per_group
        end_idx = min((g + 1) * items_per_group, total)
        groups.append(products[start_idx:end_idx])
    
    # Find max rows needed
    max_rows = max(len(g) for g in groups) if groups else 0
    
    headers = ['Mã SP', 'Tên SP', 'CAD', 'ĐẶT HÀNG', 'CNC', 'Vật tư ưu tiên', 'Vật tư']
    
    def get_cell_style(delta):
        # delta = TC - TT
        if delta == 0: return ('✔', '#1E88E5')   # TT = TC: Complete (blue)
        elif delta < 0: return ('➚', '#FFEB3B')  # TT > TC: Exceeded (yellow)
        else: return ('✖', '#F44336')            # TT < TC: Incomplete (red)
    
    # Prepare details JSON for JavaScript
    import json
    details_json = json.dumps(details_map, ensure_ascii=False, default=str)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ box-sizing: border-box; font-family: Arial, sans-serif; }}
        body {{ margin: 0; padding: 10px; background: transparent; }}
        
        .matrix-grid {{
            display: grid;
            grid-template-columns: repeat({num_groups}, 1fr);
            gap: 10px;
        }}
        
        .grid-column {{
            display: flex;
            flex-direction: column;
        }}
        
        .column-header {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            align-items: center;
            background: #1e3a5f;
            border: 1px solid #334155;
        }}
        
        .column-header span {{
            color: #e2e8f0;
            font-size: 10px;
            font-weight: 600;
            text-align: center;
            padding: 3px 2px;
            border-right: 1px solid #334155;
        }}
        
        .column-header span:nth-child(1), .column-header span:nth-child(2) {{
            writing-mode: horizontal-tb;
            transform: none;
            height: auto;
        }}
        
        .column-header span:nth-child(n+3) {{
            writing-mode: vertical-rl;
            text-orientation: mixed;
            transform: rotate(180deg);
            height: 70px;
        }}
        
        .product-row {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            border: 1px solid #334155;
            align-items: stretch; /* Ensure cells stretch to full height */
            border-top: none;
            cursor: pointer;
        }}
        
        .product-row:hover {{
            background: #334155 !important;
        }}
        
        .product-row.selected {{
            background: #2563eb !important;
        }}
        
        .product-row span {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 0; /* Required for text-overflow in flex */
            padding: 3px 4px;
            color: white;
            font-size: 11px;
            text-align: center;
            border-right: 1px solid #334155;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        /* 2nd Child (Tên SP) - Left Align */
        .product-row span:nth-child(2) {{
            justify-content: flex-start;
            text-align: left;
        }}
        
        .product-row span:first-child {{
            text-align: left;
            background: #1e293b;
            font-weight: 500;
        }}
        
        .cell-empty {{
            background: linear-gradient(to top right, transparent calc(50% - 1px), #475569, transparent calc(50% + 1px)),
                        linear-gradient(to top left, transparent calc(50% - 1px), #475569, transparent calc(50% + 1px)) !important;
        }}
        
        /* Detail Row - Full width spanning all columns */
        .detail-row {{
            display: none;
            grid-column: 1 / -1;
            border: 2px solid #334155;
            background: #0f172a;
            margin: 5px 0;
        }}
        
        .detail-row.active {{
            display: block;
        }}
        
        .detail-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        
        .detail-table th {{
            background: #1e3a5f;
            color: #e2e8f0;
            padding: 8px;
            text-align: center;
            font-weight: 600;
            border: 1px solid #334155;
        }}
        
        .detail-table td {{
            padding: 6px 10px;
            border: 1px solid #334155;
            color: #e2e8f0;
            background: #0f172a;
        }}
        
        .detail-table .product-cell {{
            text-align: center;
            vertical-align: middle;
            font-weight: bold;
            font-size: 14px;
            background: #1e293b;
            width: 120px;
        }}
        
        .detail-table .cat-cell {{
            text-align: center;
            font-weight: 500;
            width: 100px;
        }}
        
        .cat-cad {{ color: #38bdf8; }}
        .cat-cnc {{ color: #facc15; }}
        .cat-vt-ut {{ color: #f472b6; }}
        .cat-vt {{ color: #a3e635; }}
        
        .status-done { background-color: #1E88E5 !important; color: white; text-align: center; font-weight: 600; }
        .status-missing { background-color: #FFB300 !important; color: #000; text-align: center; font-weight: 600; }
        .status-extra { background-color: #D32F2F !important; color: white; text-align: center; font-weight: 600; }}
        
        .empty-cell {{
            visibility: hidden;
            height: 22px;
        }}
    </style>
    <script>
        var allDetails = {details_json};
        var selectedRow = null;
        var activeDetailRow = null;
        
        function showDetail(productCode, rowElement, detailRowId) {{
            // Deselect previous
            if (selectedRow) {{
                selectedRow.classList.remove('selected');
            }}
            if (activeDetailRow) {{
                activeDetailRow.style.display = 'none';
            }}
            
            // Select new
            rowElement.classList.add('selected');
            selectedRow = rowElement;
            
            var detailRow = document.getElementById(detailRowId);
            var tbody = detailRow.querySelector('.detail-tbody');
            var details = allDetails[productCode] || [];
            
            tbody.innerHTML = '';
            
            if (details.length === 0) {{
                tbody.innerHTML = '<tr><td class="product-cell">' + productCode + '</td><td colspan="9" style="text-align:center; color:#94a3b8;">Chưa có dữ liệu chi tiết</td></tr>';
            }} else {{
                var cadItems = details.filter(function(d) {{ return d.category === 'CAD'; }});
                var cadQty = cadItems.reduce(function(sum, d) {{ return sum + (d.quantity || 0); }}, 0);
                
                var cncItems = details.filter(function(d) {{ return d.category === 'CNC'; }});
                var cncQty = cncItems.reduce(function(sum, d) {{ return sum + (d.quantity || 0); }}, 0);
                
                var vtItems = details.filter(function(d) {{ return d.category === 'VẬT TƯ'; }});
                var vtPrio = vtItems.filter(function(d) {{ return d.is_priority; }});
                var vtNorm = vtItems.filter(function(d) {{ return !d.is_priority; }});
                
                var totalRows = 0;
                if (cadItems.length > 0) totalRows++;
                if (cncItems.length > 0) totalRows++;
                totalRows += vtPrio.length + vtNorm.length;
                if (totalRows === 0) totalRows = 1;
                
                var firstRow = true;
                
                // Helper to render product name cell only once
                var productNameStr = '';
                if (cadItems.length > 0) productNameStr = cadItems[0].product_name || '';
                else if (cncItems.length > 0) productNameStr = cncItems[0].product_name || '';
                
                if (cadItems.length > 0) {{
                    var row = '<tr>';
                    if (firstRow) {{
                        row += '<td class="product-cell" rowspan="' + totalRows + '">' + productCode + '</td>';
                        row += '<td class="product-cell" rowspan="' + totalRows + '" style="font-weight:normal; font-size:12px; width:150px;">' + productNameStr + '</td>';
                        firstRow = false;
                    }}
                    // CAD Row Content - Robust name check
                    var cadName = cadItems[0].item_name;
                    if (!cadName || cadName === 'undefined' || cadName === '') {{ cadName = cadItems[0].name; }}
                    if (!cadName || cadName === 'undefined' || cadName === '') {{ cadName = cadItems[0].product_name; }}
                    if (!cadName || cadName === 'undefined' || cadName === '') {{ cadName = 'DEBUG_CAD: ' + JSON.stringify(cadItems[0]).substring(0, 80); }}
                    row += '<td>' + cadName + '</td>';
                    row += '<td style="text-align:center;">' + cadQty + '</td>';
                    row += '<td></td>';
                    row += '<td style="text-align:center;">' + (cadItems[0].unit || '') + '</td>';
                    row += '<td style="text-align:center;">' + (cadItems[0].creation_date || '') + '</td>';
                    row += '<td></td><td></td><td></td></tr>';
                    tbody.innerHTML += row;
                }}
                
                if (cncItems.length > 0) {{
                    var row = '<tr>';
                    if (firstRow) {{
                        row += '<td class="product-cell" rowspan="' + totalRows + '">' + productCode + '</td>';
                        row += '<td class="product-cell" rowspan="' + totalRows + '" style="font-weight:normal; font-size:12px; width:150px;">' + productNameStr + '</td>';
                        firstRow = false;
                    }}
                    // CNC Row Content - Robust name check
                    var cncName = cncItems[0].item_name;
                    if (!cncName || cncName === 'undefined' || cncName === '') {{ cncName = cncItems[0].name; }}
                    if (!cncName || cncName === 'undefined' || cncName === '') {{ cncName = cncItems[0].product_name; }}
                    if (!cncName || cncName === 'undefined' || cncName === '') {{ cncName = 'DEBUG_CNC: ' + JSON.stringify(cncItems[0]).substring(0, 80); }}
                    row += '<td>' + cncName + '</td>';
                    row += '<td style="text-align:center;">' + cncQty + '</td>';
                    row += '<td></td>';
                    row += '<td style="text-align:center;">' + (cncItems[0].unit || '') + '</td>';
                    row += '<td style="text-align:center;">' + (cncItems[0].creation_date || '') + '</td>';
                    row += '<td></td><td></td><td></td></tr>';
                    tbody.innerHTML += row;
                }}
                
                for (var i = 0; i < vtPrio.length; i++) {{
                    var d = vtPrio[i];
                    console.log('[DEBUG JS vtPrio]', JSON.stringify(d));
                    var row = '<tr>';
                    if (firstRow) {{
                        row += '<td class="product-cell" rowspan="' + totalRows + '">' + productCode + '</td>';
                        row += '<td class="product-cell" rowspan="' + totalRows + '" style="font-weight:normal; font-size:12px; width:150px;">' + productNameStr + '</td>';
                        firstRow = false;
                    }}
                     // DEBUG: Robust check for name - catch 'undefined' string too
                     var nameVal = d.item_name;
                     if (!nameVal || nameVal === 'undefined' || nameVal === '') {{
                         nameVal = d.name;
                     }}
                     if (!nameVal || nameVal === 'undefined' || nameVal === '') {{
                         nameVal = d.product_name;
                     }}
                     if (!nameVal || nameVal === 'undefined' || nameVal === '') {{
                         // Show full object for debugging
                         nameVal = "DEBUG: " + JSON.stringify(d).substring(0, 100);
                     }}
                     row += '<td>' + nameVal + '</td>';
                     row += '<td style="text-align:center;">' + (d.quantity || 0) + '</td>';
                     
                     // Remaining / Tồn logic
                     // If using calculator.py's current (Xuat - Nhap), negative means "Left to do" (if Plan > Used)
                     // User likely wants "Tồn kho" (Inventory) = Plan - Used.
                     // But let's stick to reading 'remaining' and just interpreting it correctly.
                     var rem = (d.remaining !== undefined) ? d.remaining : (d.stock || 0);
                     
                     var remColor = '#94a3b8'; // gray
                     if (rem < 0) remColor = '#ef4444'; // red (missing/incomplete)
                     else if (rem > 0) remColor = '#facc15'; // yellow (extra/stock)
                     
                     row += '<td style="text-align:center; font-weight:bold; color:' + remColor + ';">' + rem + '</td>';
                     row += '<td style="text-align:center;">' + (d.unit || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.creation_date || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.date || '') + '</td>';
                     
                     // Status Logic
                     // 1. Try status_code (done, missing, extra)
                     var sc = d.status_code || '';
                     // 2. Fallback to status text
                     var stText = d.status || '';
                     
                     var statusClass = '';
                     var statusIcon = '';
                     
                     // Priority to status_code if available
                     if (sc === 'done' || stText === 'Hoàn thành' || stText === 'Đủ') {{ statusClass = 'status-done'; statusIcon = '✔ '; }}
                     else if (sc === 'missing' || stText === 'Đang làm' || stText === 'Thiếu') {{ statusClass = 'status-missing'; statusIcon = '⏳ '; }}
                     else if (sc === 'extra' || stText === 'Phát sinh' || stText === 'Vượt KH' || stText === 'Dư') {{ statusClass = 'status-extra'; statusIcon = '⚠ '; }}
                     
                     row += '<td class="' + statusClass + '">' + statusIcon + stText + '</td>'; 
                     row += '<td>' + (d.note || '') + '</td>';
                     row += '</tr>';
                     tbody.innerHTML += row;
                 }}
                 
                 for (var i = 0; i < vtNorm.length; i++) {{
                     var d = vtNorm[i];
                     var row = '<tr>';
                     if (firstRow) {{
                         row += '<td class="product-cell" rowspan="' + totalRows + '">' + productCode + '</td>';
                         row += '<td class="product-cell" rowspan="' + totalRows + '" style="font-weight:normal; font-size:12px; width:150px;">' + productNameStr + '</td>';
                         firstRow = false;
                     }}
                     // DEBUG: Robust check for name - catch 'undefined' string too
                     var nameVal = d.item_name;
                     if (!nameVal || nameVal === 'undefined' || nameVal === '') {{
                         nameVal = d.name;
                     }}
                     if (!nameVal || nameVal === 'undefined' || nameVal === '') {{
                         nameVal = d.product_name;
                     }}
                     if (!nameVal || nameVal === 'undefined' || nameVal === '') {{
                         nameVal = "DEBUG: " + JSON.stringify(d).substring(0, 100);
                     }}
                     row += '<td>' + nameVal + '</td>';
                     row += '<td style="text-align:center;">' + (d.quantity || 0) + '</td>';
                     
                     var rem = (d.remaining !== undefined) ? d.remaining : (d.stock || 0);
                     var remColor = '#94a3b8';
                     if (rem < 0) remColor = '#ef4444';
                     else if (rem > 0) remColor = '#facc15';
                     
                     row += '<td style="text-align:center; font-weight:bold; color:' + remColor + ';">' + rem + '</td>';
                     row += '<td style="text-align:center;">' + (d.unit || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.creation_date || '') + '</td>';
                     row += '<td style="text-align:center;">' + (d.date || '') + '</td>';
                     
                      // Status Logic (Copy same logic)
                     var sc = d.status_code || '';
                     var stText = d.status || '';
                     var statusClass = '';
                     var statusIcon = '';
                     
                     if (sc === 'done' || stText === 'Hoàn thành' || stText === 'Đủ') {{
                         statusClass = 'status-done';
                         statusIcon = '✔';
                     }} else if (sc === 'missing' || stText === 'Đang làm' || (rem > 0)) {{
                         statusClass = 'status-extra';
                         statusIcon = '⏳';
                     }} else if (sc === 'extra' || stText === 'Phát sinh' || stText === 'Vượt KH' || (rem < 0)) {{
                         statusClass = 'status-missing';
                         statusIcon = '⚠';
                     }}

                     row += '<td class="' + statusClass + '">' + (statusIcon || stText) + '</td>';
                     row += '<td>' + (d.note || '') + '</td></tr>';
                     tbody.innerHTML += row;
                 }}
                
                if (totalRows === 0) {{
                    tbody.innerHTML = '<tr><td class="product-cell">' + productCode + '</td><td colspan="9" style="text-align:center; color:#94a3b8;">Chưa có dữ liệu</td></tr>';
                }}
            }}
            
            detailRow.style.display = 'block';
            activeDetailRow = detailRow;
        }}
    </script>
    </head>
    <body>
    """
    
    # Build row-by-row (each row has products from all groups at same index position)
    for row_idx in range(max_rows):
        # Start a visual row container
        html += '<div class="matrix-grid">'
        
        # Add header if first row
        if row_idx == 0:
            for g in range(num_groups):
                html += '<div class="column-header">'
                for h in headers:
                    html += f'<span>{h}</span>'
                html += '</div>'
            html += '</div><div class="matrix-grid">'
        
        # Add product cells for each group
        for g in range(num_groups):
            if row_idx < len(groups[g]):
                prod = groups[g][row_idx]
                row_data = matrix_df.loc[prod] if prod in matrix_df.index else {}
                
                def get_cell(tc_key, tt_key):
                    tc = row_data.get(tc_key, 0)
                    tt = row_data.get(tt_key, 0)
                    if tc > 0:
                        icon, color = get_cell_style(tc - tt)
                        return f'<span style="background:{color};">{icon}</span>'
                    return '<span class="cell-empty"></span>'
                
                safe_prod = prod.replace("'", "\\'").replace('"', '\\"')
                detail_row_id = f'detail_row_{row_idx}'
                
                html += f'<div class="grid-column"><div class="product-row" onclick="showDetail(\'{safe_prod}\', this, \'{detail_row_id}\')">'
                html += f'<span>{prod}</span>'
                html += f'<span style="text-align:left !important; padding-left:4px; font-weight:normal;" title="{row_data.get("TEN_SP", "")}">{row_data.get("TEN_SP", "")}</span>'
                html += get_cell('CAD_TC', 'CAD_TT')
                html += get_cell('DAT_HANG_TC', 'DAT_HANG_TT')
                html += get_cell('CNC_TC', 'CNC_TT')
                html += get_cell('VAT_TU_UU_TIEN_TC', 'VAT_TU_UU_TIEN_TT')
                html += get_cell('VAT_TU_TC', 'VAT_TU_TT')
                html += '</div></div>'
            else:
                # Empty placeholder for alignment
                html += '<div class="grid-column"><div class="product-row empty-cell"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div></div>'
        
        html += '</div>'  # End matrix-grid row
        
        # Add detail row placeholder (full-width, hidden by default)
        detail_row_id = f'detail_row_{row_idx}'
        html += f'''
        <div id="{detail_row_id}" class="detail-row">
            <table class="detail-table">
                <thead>
                    <tr>
                        <th style="width:90px;">Mã SP</th>
                        <th>TÊN SP</th>
                        <th>TÊN HÀNG</th>
                        <th style="width:60px;">SỐ LƯỢNG</th>
                        <th style="width:50px;">TỒN</th>
                        <th style="width:55px;">ĐƠN VỊ</th>
                        <th style="width:100px;">NGÀY LẬP DS</th>
                        <th style="width:100px;">HOÀN THÀNH</th>
                        <th style="width:85px;">TRẠNG THÁI</th>
                        <th style="width:100px;">GHI CHÚ</th>
                    </tr>
                </thead>
                <tbody class="detail-tbody"></tbody>
            </table>
        </div>
        '''
    
    html += '</body></html>'
    return html

if st.session_state.selected_contract:
    st.markdown("---")
    st.markdown(f"### 📋 Bảng Matrix Chi tiết")
    
    files = []
    if st.session_state.data_source == 'Google Drive':
        contract_id = st.session_state.contracts_map.get(st.session_state.selected_contract)
        if contract_id:
             files = load_data_from_drive(contract_id)
    else:
         contract_path = os.path.join(st.session_state.local_root_path, str(st.session_state.selected_year), st.session_state.selected_contract)
         files = scan_project_files(contract_path)
    
    if files:
        matrix = build_matrix_table(files)
        
        if not matrix.empty:
            # Load ALL Details
            from src.core.calculator import get_all_product_details
            details_map = get_all_product_details(files)
            
            # Render HTML with details embedded
            html_content = render_matrix_grids_html(matrix, details_map)
            
            # Calculate height based on total products
            total_height = 150 + (len(matrix) * 30) + 400  # header + rows + detail panel buffer
            
            components.html(html_content, height=total_height, scrolling=True)
            
            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Tổng Mã SP", len(matrix))
            with col2:
                if 'CAD_TC' in matrix.columns and 'CAD_TT' in matrix.columns:
                    complete = ((matrix['CAD_TC'] - matrix['CAD_TT']) == 0).sum()
                    st.metric("✅ CAD Hoàn thành", f"{complete}/{len(matrix)}")
            with col3:
                if 'CNC_TC' in matrix.columns and 'CNC_TT' in matrix.columns:
                    complete = ((matrix['CNC_TC'] - matrix['CNC_TT']) == 0).sum()
                    st.metric("✅ CNC Hoàn thành", f"{complete}/{len(matrix)}")
        else:
            st.warning("Không có dữ liệu Matrix cho hợp đồng này.")
    else:
        st.warning("Không tìm thấy file Excel trong hợp đồng này.")

