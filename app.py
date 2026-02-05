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
from src.ui.design import Labels
from src.ui.components import render_master_table_html, render_timeline_html, render_matrix_grids_html
from src.core.cache_manager import (
    drive_client, 
    get_available_years_drive, 
    get_contracts_for_year_drive, 
    load_data_from_drive, 
    load_all_contracts_data_logic, 
    get_available_years_local, 
    get_contracts_for_year_local, 
    load_all_contracts_data_local
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
        selected_year = st.selectbox(Labels.LABEL_YEAR, years_list, index=0)
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
            if st.button(Labels.BTN_LOAD_DATA, use_container_width=True):
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
            
            st.markdown(f"### {Labels.HEADER_DETAILS}")
            selected_contract = st.selectbox(Labels.LABEL_CONTRACT, [Labels.OPTION_DEFAULT] + c_list)
            if selected_contract != Labels.OPTION_DEFAULT:
                st.session_state.selected_contract = selected_contract
            else:
                st.session_state.selected_contract = None
            
    # LOCAL HDD MODE
    else:
        local_path = st.text_input(Labels.LABEL_LOCAL_PATH, value=st.session_state.local_root_path)
        st.session_state.local_root_path = local_path
        
        years = get_available_years_local(local_path)
        if years:
            selected_year = st.selectbox(Labels.LABEL_YEAR, years, index=0)
            st.session_state.selected_year = selected_year
            
            if st.button(f"{Labels.BTN_LOAD_PROJECTS} (Local)", use_container_width=True):
                with st.spinner("Đang quét ổ cứng..."):
                    st.session_state.master_data = load_all_contracts_data_local(local_path, selected_year)
                    st.success(f"✅ Đã tải năm {selected_year}!")
                    st.rerun()
            
            st.markdown("---")
            
            if st.session_state.master_data:
                contracts = get_contracts_for_year_local(local_path, selected_year)
                st.markdown(f"### {Labels.HEADER_DETAILS}")
                selected_contract = st.selectbox(Labels.LABEL_CONTRACT, [Labels.OPTION_DEFAULT] + contracts)
                if selected_contract != Labels.OPTION_DEFAULT:
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
st.markdown(f"### {Labels.HEADER_OVERVIEW}")

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
        st.markdown(f"### {Labels.HEADER_CONTRACT_PREFIX} {contract_name}")
        
        
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
