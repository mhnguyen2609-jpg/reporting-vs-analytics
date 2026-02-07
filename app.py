import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import sys
import math
import io
import time

print("DEBUG: Starting app.py...")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.file_scanner import scan_drive_files, scan_project_files
from src.core.calculator import calculate_aggregates, build_matrix_table, get_all_product_details, extract_milestones_from_files
from src.utils.drive_adapter import GoogleDriveClient
from src.core.constants import DEFAULT_ROOT_PATH
from src.ui.design import Labels
from src.ui.components import render_master_table_html, render_timeline_html, render_matrix_grids_html, render_material_stats_html
from src.core.material_aggregator import aggregate_materials_by_name
from src.core.cache_manager import (
    get_drive_client_v3, 
    get_available_years_drive, 
    get_contracts_for_year_drive, 
    load_data_from_drive, 
    load_all_contracts_data_logic, 
    get_available_years_local, 
    get_contracts_for_year_local, 
    load_all_contracts_data_local,
    load_shared_cache
)

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title=Labels.PAGE_TITLE,
    page_icon=Labels.PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global CSS for Arial font
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: Arial, sans-serif; }
    
    /* Transparent Dataframe */
    [data-testid="stDataFrame"] { background-color: transparent !important; }
    [data-testid="stTable"] { background-color: transparent !important; }
    .stDataFrame { background-color: transparent !important; }
    
    /* 1. Sidebar Background Matching & Z-Index Promotion */
    section[data-testid="stSidebar"] {
        background-color: #0e1117; /* Matches default dark main bg */
        z-index: 10000 !important; /* Above Loader */
    }
    
    /* 2. Sidebar Buttons (Tổng quan, Chi tiết) - Transparent */
    /* Target buttons inside sidebar */
    section[data-testid="stSidebar"] button {
        background-color: transparent !important;
        border: none !important;
        color: #fafafa !important;
        text-align: left !important;
    }
    
    section[data-testid="stSidebar"] button:hover {
        background-color: #262730 !important; /* Slight hover effect */
        color: #ffffff !important;
    }

    /* Adjust specific buttons if needed, but the above covers the request for sidebar buttons */
</style>
""", unsafe_allow_html=True)

from src.utils.helpers import natural_sort_key


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
if 'milestones' not in st.session_state:
    st.session_state.milestones = []  # List of milestone dicts
if 'local_details_cache' not in st.session_state:
    st.session_state.local_details_cache = {}
    
# Logic Flag for Auto-Load 2026 (Run once)
if 'is_initialized' not in st.session_state:
    st.session_state.is_initialized = False
    
# Page Navigation State
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Tổng quan"

# ============================================================
# SIDEBAR
# ============================================================
# GLOBAL LOADER PLACEHOLDER (Use this to force rendering in Main Area)
global_loader_placeholder = st.empty()

with st.sidebar:
    # 1. Page Navigation (Vertical Buttons)
    if st.button("📊 Tổng quan", use_container_width=True, 
                type="primary" if st.session_state.current_page == "Tổng quan" else "secondary"):
        st.session_state.current_page = "Tổng quan"
        st.rerun()
    
    if st.button("🏗️ Chi tiết", use_container_width=True, 
                type="primary" if st.session_state.current_page == "Chi tiết dự án" else "secondary"):
        st.session_state.current_page = "Chi tiết dự án"
        st.rerun()
            
    st.markdown("---")

    # 2. Source Selection
    source = st.selectbox("Nguồn dữ liệu", ["Google Drive", "Local HDD (Offline)"], 
                        index=0 if st.session_state.data_source == 'Google Drive' else 1)
    st.session_state.data_source = source

    # Defines for Google Drive
    YEAR_FOLDERS = {
        '2026': '1hn-nFm56a3X24qs3WbweJfx6BqJ9ggr6',
        '2025': '1YoRBhoWDXMB4-byVtyqHHNKM1PVKbptd',
    }
    
    # CSS for Custom Loading Spinner (Multi-Ring & Centered)
    st.markdown("""
    <style>
    /* Ensure Main Content is relative for absolute positioning of loader */
    section[data-testid="stMain"] {
        position: relative !important;
    }

    .loader-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        min-height: 100vh;
        background: rgba(15, 23, 42, 0.9);
        z-index: 9999; /* Covers Main Content */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .loader-ring {
        display: inline-block;
        position: relative;
        width: 80px;
        height: 80px;
    }
    .loader-ring div {
        box-sizing: border-box;
        display: block;
        position: absolute;
        width: 64px;
        height: 64px;
        margin: 8px;
        border: 8px solid #3b82f6;
        border-radius: 50%;
        animation: loader-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
        border-color: #3b82f6 transparent transparent transparent;
    }
    .loader-ring div:nth-child(1) { animation-delay: -0.45s; }
    .loader-ring div:nth-child(2) { animation-delay: -0.3s; }
    .loader-ring div:nth-child(3) { animation-delay: -0.15s; }
    @keyframes loader-ring {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .loading-text {
        margin-top: 20px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 18px;
        color: #e2e8f0;
        font-weight: 500;
    }
    .loading-percent {
        font-size: 14px;
        color: #94a3b8;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    # AUTO-LOAD LOGIC
    # Ensure session state structure
    if "master_data" not in st.session_state: st.session_state.master_data = []

    print("DEBUG: Auto-load Check (DISABLED)")
    # --- AUTO-LOAD DATA ON STARTUP (2026) ---
    if "data_loaded" not in st.session_state:
         # TEMPORARILY DISABLED TO DEBUG SEGFAULT
         st.session_state.data_loaded = True # Skip
         pass
         
         # ----------------------------------------------------
         # ORIGINAL LOGIC BELOW (COMMENTED OUT)
         # ----------------------------------------------------
         # AUTO-LOAD LOGIC
         # AUTO-LOAD LOGIC
         # if not st.session_state.is_initialized:
         #     # 1. Determine Target Source & Year
         #     target_year = '2026'
             
         #     # Check Local Presence
         #     has_local = os.path.exists(st.session_state.local_root_path)
             
         #     # Deciding Default Source: Prefer Local if available and configured, else Drive
         #     # But for this specific User Request, let's allow "Smart" default
         #     if has_local:
         #          source = 'Local HDD (Offline)'
         #          st.session_state.data_source = source
         #     else:
         #          source = 'Google Drive'
         #          st.session_state.data_source = source

         #     st.session_state.selected_year = target_year
         #     start_auto_load = True
                 
         #     if start_auto_load:
         #         # 2. Main Area Loader Placeholder
         #         loader_placeholder = global_loader_placeholder
                 
         #         def update_progress(percent, message):
         #             loader_placeholder.markdown(f"""
         #             <div class="loader-overlay">
         #                 <div class="loader-ring"><div></div><div></div><div></div><div></div></div>
         #                 <div class="loading-text">{message}</div>
         #                 <div class="loading-percent">{int(percent * 100)}%</div>
         #             </div>
         #             """, unsafe_allow_html=True)

         #         try:
         #             # Load Master Data based on Source
         #             if source == 'Google Drive':
         #                 st.session_state.drive_root_id = YEAR_FOLDERS.get(target_year)
         #                 st.session_state.years_map = YEAR_FOLDERS
         #                 st.session_state.master_data = load_all_contracts_data_logic(
         #                     target_year, YEAR_FOLDERS, progress_callback=update_progress)
         #             else: # Local HDD
         #                  st.session_state.master_data = load_all_contracts_data_local(
         #                      st.session_state.local_root_path, target_year, progress_callback=update_progress)
                 
         #         except Exception as e:
         #             st.error(f"Lỗi khởi động: {e}")
                     
         #         st.session_state.is_initialized = True
         #         loader_placeholder.empty()
         #         st.rerun()
                 
    # SOURCE CONTROLS
    if source == 'Google Drive':
        years_list = list(YEAR_FOLDERS.keys())
        idx = 0
        if st.session_state.selected_year in years_list:
             idx = years_list.index(st.session_state.selected_year)
        selected_year = st.selectbox(Labels.LABEL_YEAR, years_list, index=idx)
        
        if selected_year != st.session_state.selected_year:
             st.session_state.selected_year = selected_year
             st.session_state.drive_root_id = YEAR_FOLDERS[selected_year]

        col1, col2 = st.columns(2)
        with col1:
            if st.button(Labels.BTN_LOAD_DATA, use_container_width=True):
                 # Manual Load logic with Overlay
                loader_placeholder = global_loader_placeholder
                def update_progress_manual(percent, message):
                    loader_placeholder.markdown(f"""
                    <div class="loader-overlay">
                        <div class="loader-ring"><div></div><div></div><div></div><div></div></div>
                        <div class="loading-text">{message}</div>
                        <div class="loading-percent">{int(percent * 100)}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.session_state.master_data = load_all_contracts_data_logic(
                    selected_year, YEAR_FOLDERS, progress_callback=update_progress_manual)
                
                loader_placeholder.empty()
                st.success(f"✅ Đã tải năm {selected_year}!")
                st.rerun()

        with col2:
            if st.button("🔃 Làm mới", use_container_width=True, help="Bỏ qua cache"):
                loader_placeholder = global_loader_placeholder
                def update_progress_refresh(percent, message):
                    loader_placeholder.markdown(f"""
                    <div class="loader-overlay">
                        <div class="loader-ring"><div></div><div></div><div></div><div></div></div>
                        <div class="loading-text">{message}</div>
                        <div class="loading-percent">{int(percent * 100)}%</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.session_state.master_data = load_all_contracts_data_logic(
                    selected_year, YEAR_FOLDERS, force_reload=True, progress_callback=update_progress_refresh)
                
                loader_placeholder.empty()
                st.success(f"✅ Đã làm mới năm {selected_year}!")
                st.rerun()
        st.markdown("---")

    # LOCAL HDD CONTROLS
    elif source == 'Local HDD (Offline)':
        st.info("📂 Chế độ Local HDD (Ngoại tuyến)")
        root_path = st.text_input("Đường dẫn gốc:", value=st.session_state.local_root_path)
        if root_path and os.path.exists(root_path):
            st.session_state.local_root_path = root_path
            years = get_available_years_local(root_path)
            st.markdown(f"""
            <div style="background: transparent; border: 1px solid rgba(255,255,255,0.1); padding: 16px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="margin-top:0; color: #cbd5e1;">📊 Thống kê Tổng quan ({st.session_state.selected_year})</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #38bdf8;">{0}</div>
                        <div style="font-size: 13px; color: #94a3b8;">Hợp đồng</div>
                    </div>
                     <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: {'#f87171'};">{'N/A'}</div>
                        <div style="font-size: 13px; color: #94a3b8;">Trạng thái</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #fbbf24;">{0.0:.1f}%</div>
                        <div style="font-size: 13px; color: #94a3b8;">Tiến độ TB</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if years:
                selected_year = st.selectbox(Labels.LABEL_YEAR, years)
                st.session_state.selected_year = selected_year
                
                if st.button(Labels.BTN_LOAD_DATA, use_container_width=True):
                    # Manual Load with Overlay
                    loader_placeholder = global_loader_placeholder
                    def update_progress_local(percent, message):
                        loader_placeholder.markdown(f"""
                        <div class="loader-overlay">
                            <div class="loader-ring"><div></div><div></div><div></div><div></div></div>
                            <div class="loading-text">{message}</div>
                            <div class="loading-percent">{int(percent * 100)}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.session_state.master_data = load_all_contracts_data_local(
                        root_path, selected_year, progress_callback=update_progress_local)
                    
                    loader_placeholder.empty()
                    st.rerun()
            else:
                st.warning("Không tìm thấy thư mục năm nào (vd: 2024, 2025).")
        else:
            st.error("Đường dẫn không tồn tại.")
            
    # Contract Selector (Shared Logic)
    if st.session_state.master_data:
        # Determine current Contracts list based on Source logic or just Master Data mapping
        # Since master_data is unified list of dicts, we can extract contracts
        # But for Details View we need the mapping keys/path
        
        # Simplified: Just extract unique contract names from master data
        c_list = sorted(list(set([d['contract'] for d in st.session_state.master_data])), key=natural_sort_key)
        
        st.markdown(f"### {Labels.HEADER_DETAILS}")
        
        c_idx = 0
        if st.session_state.selected_contract in c_list:
            c_idx = c_list.index(st.session_state.selected_contract) + 1
            
        selected_contract = st.selectbox(Labels.LABEL_CONTRACT, [Labels.OPTION_DEFAULT] + c_list, index=c_idx)
        
        if selected_contract != Labels.OPTION_DEFAULT:
            st.session_state.selected_contract = selected_contract
        else:
            # If "Select..." is chosen, default to the FIRST contract if available (Auto-select)
            # This handles the "Not auto loading" complaint by ensuring a contract is always active
            if c_list:
                st.session_state.selected_contract = c_list[0]
                # We need to rerun to update the selectbox index visually if we want sync?
                # Or just let it render.
                # If we change session_state here, next rerun will pick it up.
                st.rerun()
            else:
                st.session_state.selected_contract = None

# ============================================================
# MAIN AREA
# ============================================================

# PAGE 1: TỔNG QUAN
if st.session_state.current_page == "Tổng quan":
    st.markdown(f"### {Labels.HEADER_OVERVIEW}")

    if st.session_state.master_data is not None:
        if st.session_state.master_data:
            html = render_master_table_html(st.session_state.master_data)
            
            # Determine unique contracts for height calc
            unique_contracts = set([d['contract'] for d in st.session_state.master_data])
            num_contracts = len(unique_contracts)
            
            # Height: 7 rows/contract * ~35px/row + Buffer
            height = min(max(300, num_contracts * 7 * 35 + 100), 1200)
            components.html(html, height=height, scrolling=True)
        else:
            st.warning("📭 Không tìm thấy dữ liệu nào cho năm đã chọn.")
    else:
        st.info("👋 Chào mừng! Vui lòng nhấn **Tải dữ liệu** ở Sidebar để bắt đầu.")


# PAGE 2: CHI TIẾT DỰ ÁN
elif st.session_state.current_page == "Chi tiết dự án":
    contracts_to_render = []

    if st.session_state.selected_contract:
        contracts_to_render = [st.session_state.selected_contract]
    else:
        # Show ALL contracts (sorted naturally) if no specific one selected?
        # Or perhaps prompt to select?
        # User request: "Details logic (Timeline, Matrix...)"
        if st.session_state.contracts_map:
            contracts = list(st.session_state.contracts_map.keys())
            contracts_to_render = sorted(contracts, key=natural_sort_key)
        else:
             st.info("Chưa có danh sách hợp đồng. Vui lòng tải dữ liệu.")

    if contracts_to_render:
        # Pre-load details cache
        details_cache = st.session_state.get('details_cache', {})
        master_data = st.session_state.get('master_data', [])
        
        stats_map = {}
        if master_data:
            for row in master_data:
                if 'contract' in row: stats_map[row['contract']] = row

        if not details_cache and len(contracts_to_render) > 1:
            st.warning("⚠️ Dữ liệu chi tiết chưa được tải đầy đủ. Vui lòng nhấn **'Tải dữ liệu'** để xem.")

        for contract_name in contracts_to_render:
            
            # --- LOAD FILE DATA LOGIC ---
            contract_files = []
            
            # Common Logic: ID resolution
            c_id = st.session_state.contracts_map.get(contract_name)
            
            if st.session_state.data_source == 'Google Drive':
                if c_id and c_id in details_cache:
                    cached_files = details_cache[c_id]
                    import base64
                    for f in cached_files:
                        new_f = f.copy()
                        content = f.get('content')
                        if isinstance(content, str):
                            try: new_f['content'] = base64.b64decode(content)
                            except: pass
                        contract_files.append(new_f)
                elif c_id and len(contracts_to_render) == 1:
                    contract_files = load_data_from_drive(c_id)
            
            elif st.session_state.data_source == 'Local HDD (Offline)':
                if c_id:
                     if c_id in details_cache:
                         contract_files = details_cache[c_id]
                     else:
                         # Fallback if not in cache (shouldn't happen with auto-load, but safe to have)
                         from src.utils.file_scanner import scan_project_files
                         contract_files = scan_project_files(c_id)
            
            # --- HEADER & STATS BAR ---
            st.markdown(f"### {Labels.HEADER_CONTRACT_PREFIX} {contract_name}")
            
            # Calculate Stats
            aggs = {}
            if contract_files:
                aggs = calculate_aggregates(contract_files)
                
            if not contract_files and contract_name in stats_map:
                row = stats_map[contract_name]
                def parse_stat(val):
                    if isinstance(val, str) and '/' in val:
                        p = val.split('/')
                        return {'TT': int(p[0]), 'TC': int(p[1])}
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
            <div style="background: transparent; border: 1px solid rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 8px; margin: 8px 0; font-size: 13px; color: #cbd5e1; font-family: Arial, sans-serif;">
                <span style="margin-right: 24px;"><b>Shop duyệt:</b> {int(cad_stats['TT'])}/{int(cad_stats['TC'])}</span>
                <span style="margin-right: 24px;"><b>Ván:</b> {int(van_stats['TT'])}/{int(van_stats['TC'])}</span>
                <span style="margin-right: 24px;"><b>Sản xuất:</b> {int(cnc_stats['TT'])}/{int(cnc_stats['TC'])}</span>
                <span><b>Vật tư:</b> {int(vt_stats['TT'])}/{int(vt_stats['TC'])}</span>
            </div>
            """, unsafe_allow_html=True)

            # DEBUG: Check for unknown files
            unknown_files = [f['filename'] for f in contract_files if not f.get('source_type')]
            if unknown_files:
                with st.expander(f"⚠️ {len(unknown_files)} File không nhận diện được (Click để xem)", icon="⚠️"):
                    st.write("Các file sau không đúng quy tắc đặt tên (DMVTN, SHOP, v.v.):")
                    st.write(unknown_files)
                    st.caption("Vui lòng đổi tên file hoặc thư mục chứa file để phần mềm nhận diện.")

            # --- TIMELINE ---
            st.markdown("#### 📅 Trục Thời Gian")
            
            auto_milestones = []
            if contract_files:
                auto_milestones = extract_milestones_from_files(contract_files)
                
            # Combine Milestones Logic (Previously implemented)
            contract_milestone_key = f"milestones_{contract_name}"
            if contract_milestone_key not in st.session_state: st.session_state[contract_milestone_key] = []
            
            # Helper: Normalize Date
            def normalize_date(d_str):
                try:
                    if '-' in d_str and len(d_str.split('-')[0]) == 4: return d_str
                    if '/' in d_str:
                         p = d_str.split('/')
                         if len(p) == 2: return f"{st.session_state.selected_year}-{p[1]}-{p[0]}"
                         if len(p) == 3: return f"{p[2]}-{p[1]}-{p[0]}"
                except: pass
                return None
            
            # Merge Auto + Manual
            merged_milestones = {}
            for m in auto_milestones:
                key = normalize_date(m.get('full_date', m.get('date')))
                if key and key not in merged_milestones: merged_milestones[key] = m.copy()
            
            for m in st.session_state[contract_milestone_key]:
                key = normalize_date(m.get('full_date', m.get('date')))
                if not key: continue
                if key in merged_milestones:
                    existing = merged_milestones[key]
                    if m.get('desc'):
                         existing['desc'] = (existing.get('desc', '') + "<br>" + m['desc']) if existing.get('desc') else m['desc']
                else:
                    merged_milestones[key] = m.copy()
            
            all_milestones = sorted(merged_milestones.values(), key=lambda x: normalize_date(x.get('full_date', x.get('date'))) or "9999")
            
            # MANUAL ADD FORM
            if "form_reset_id" not in st.session_state: st.session_state["form_reset_id"] = 0
            
            with st.expander("📅 Quản lý mốc thời gian", expanded=False):
                 edit_key_idx = f"edit_idx_{contract_name}"
                 if edit_key_idx not in st.session_state: st.session_state[edit_key_idx] = None
                 is_editing = st.session_state[edit_key_idx] is not None
                 edit_idx = st.session_state[edit_key_idx]
                 
                 from datetime import date, datetime
                 pre_date = date.today()
                 pre_desc = ""
                 pre_type = "Kế hoạch"
                 
                 if is_editing and 0 <= edit_idx < len(st.session_state[contract_milestone_key]):
                     m = st.session_state[contract_milestone_key][edit_idx]
                     try: pre_date = datetime.strptime(m.get('full_date', m.get('date')), "%Y-%m-%d").date()
                     except: pass
                     pre_desc = m.get('desc', '')

                 with st.form(key=f"form_mile_{contract_name}"):
                     c1, c2 = st.columns([1,1])
                     rid = st.session_state["form_reset_id"]
                     with c1: md = st.date_input("Ngày", value=pre_date, key=f"d_{contract_name}_{rid}", format="DD/MM/YYYY")
                     with c2: mt = st.selectbox("Loại", ["Ghi chú", "Kế hoạch"], index=0, key=f"t_{contract_name}_{rid}")
                     mdesc = st.text_area("Mô tả", value=pre_desc, height=80, key=f"de_{contract_name}_{rid}")
                     
                     if st.form_submit_button("💾 Lưu Mốc"):
                         std_date = md.strftime("%Y-%m-%d")
                         new_m = {"date": md.strftime("%d/%m/%Y"), "full_date": std_date, "desc": mdesc}
                         if is_editing:
                             st.session_state[contract_milestone_key][edit_idx] = new_m
                             st.session_state[edit_key_idx] = None
                         else:
                             st.session_state[contract_milestone_key].append(new_m)
                             st.session_state["form_reset_id"] += 1
                         st.rerun()
                
                 if st.session_state[contract_milestone_key]:
                     for idx, m in enumerate(st.session_state[contract_milestone_key]):
                         c1, c2, c3 = st.columns([1, 4, 1])
                         c1.write(f"**{m['date']}**")
                         c2.text(m['desc'])
                         if c3.button("Xóa", key=f"del_{contract_name}_{idx}"):
                             st.session_state[contract_milestone_key].pop(idx)
                             st.rerun()

            # Render Timeline Control
            if all_milestones:
                timeline_html = render_timeline_html(all_milestones)
                components.html(timeline_html, height=600, scrolling=True)
            else:
                st.caption("Chưa có dữ liệu timeline.")

            # --- MATRIX / DETAILS ---
            st.markdown("#### 📦 Chi tiết Vật tư & Sản phẩm")
            
            matrix = pd.DataFrame()
            details_map = {}
            if contract_files:
                 # Check cache for Matrix
                 matrix = build_matrix_table(contract_files)
                 if not matrix.empty:
                     details_map = get_all_product_details(contract_files)
            
            if not matrix.empty:
                 c_s, c_v = st.columns([3, 1])
                 search_term = c_s.text_input("Tìm kiếm", placeholder="Nhập mã hoặc tên...", key=f"s_{contract_name}")
                 view_mode = c_v.selectbox("Xem theo", ["Matrix (Sản phẩm)", "Tổng hợp Vật tư"], key=f"v_{contract_name}")
                 
                 if view_mode == "Matrix (Sản phẩm)":
                     filtered = matrix
                     if search_term:
                         term = search_term.lower()
                         m_reset = matrix.reset_index()
                         mask = m_reset['index'].astype(str).str.lower().str.contains(term) | \
                                m_reset['TEN_SP'].astype(str).str.lower().str.contains(term)
                         keys = m_reset[mask]['index'].tolist()
                         filtered = matrix.loc[matrix.index.isin(keys)]
                     
                     html = render_matrix_grids_html(filtered, details_map)
                     h = 100 + (len(filtered)*32) + 150
                     components.html(html, height=h, scrolling=True)
                 else:
                     mat_df = aggregate_materials_by_name(details_map)
                     if search_term:
                         mat_df = mat_df[mat_df['Tên hàng'].astype(str).str.lower().str.contains(search_term.lower())]
                     
                     html = render_material_stats_html(mat_df)
                     h = 100 + (len(mat_df)*40) + 50
                     components.html(html, height=min(1500, h), scrolling=True)
            else:
                 st.info("Không có dữ liệu chi tiết cho hợp đồng này.")
            
            st.divider() 

# Function definition must remain outside loop
