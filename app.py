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

from src.utils.file_scanner import scan_drive_files
from src.core.calculator import calculate_aggregates, build_matrix_table, get_all_product_details
from src.utils.drive_adapter import GoogleDriveClient

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
def get_drive_client_v2():
    return GoogleDriveClient()

drive_client = get_drive_client_v2()

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
    """
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

def load_all_contracts_data_logic(selected_year, years_map):
    year_id = years_map.get(str(selected_year))
    if not year_id: return []
    
    contracts_map, contracts_list = get_contracts_for_year_drive(year_id)
    all_rows = []
    categories = ['CAD', 'CNC', 'VÁN', 'VẬT TƯ', 'VẬT TƯ ƯU TIÊN']
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_contracts = len(contracts_list)
    if total_contracts == 0: return []
    
    for idx, contract_name in enumerate(contracts_list):
        contract_id = contracts_map[contract_name]
        status_text.text(f"Đang xử lý dự án: {contract_name} ({idx+1}/{total_contracts})")
        progress_bar.progress((idx) / total_contracts)
        
        # Load data (files + content)
        files = load_data_from_drive(contract_id)
        
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
if 'years_map' not in st.session_state:
    st.session_state.years_map = {}
if 'contracts_map' not in st.session_state:
    st.session_state.contracts_map = {}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🏭 Quản lý Sản xuất")
    st.markdown("---")
    
    # Input Root ID if not set
    root_id_input = st.text_input("Folder ID Gốc (Root)", value=st.session_state.drive_root_id)
    if root_id_input:
        # Auto-extract ID if user pastes a full URL
        clean_id = root_id_input.strip()
        if "drive.google.com" in clean_id:
            # Try to start finding 'folders/' pattern
            match = re.search(r'folders/([a-zA-Z0-9_-]+)', clean_id)
            if match:
                clean_id = match.group(1)
        st.session_state.drive_root_id = clean_id
    
    if st.session_state.drive_root_id:
        years_map, years_list = get_available_years_drive(st.session_state.drive_root_id)
        st.session_state.years_map = years_map
        
        if years_list:
            selected_year = st.selectbox("📅 Chọn Năm", years_list, index=0)
            st.session_state.selected_year = selected_year
            
            if st.button("🔄 Tải tất cả dự án", use_container_width=True):
                with st.spinner("Đang quét và tải dữ liệu từ Drive..."):
                    st.session_state.master_data = load_all_contracts_data_logic(selected_year, years_map)
                    st.success(f"✅ Đã tải năm {selected_year}!")
                    st.rerun()
            
            st.markdown("---")
            
            if st.session_state.master_data:
                # Get contracts list (could fetch from Drive or deduce from master_data)
                # Fetching from Drive is safer for 'selecting' a contract to view details
                # because master_data might be filtered or simplified.
                # But to save API calls, let's use the helper cache
                year_id = years_map.get(str(selected_year))
                c_map, c_list = get_contracts_for_year_drive(year_id)
                st.session_state.contracts_map = c_map
                
                st.markdown("### 📁 Xem chi tiết")
                selected_contract = st.selectbox("Chọn Hợp đồng", ["-- Chọn --"] + c_list)
                if selected_contract != "-- Chọn --":
                    st.session_state.selected_contract = selected_contract
                else:
                    st.session_state.selected_contract = None
        else:
             st.warning("Không tìm thấy thư mục Năm nào hoặc Folder ID sai.")
    else:
        st.info("Vui lòng nhập Google Drive Folder ID chuỗi dự án.")

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
if st.session_state.selected_contract:
    st.markdown("---")
    st.markdown(f"### 📅 Timeline: `{st.session_state.selected_contract}`")
    
    # Input Row
    col_date, col_desc, col_notes, col_actions = st.columns([1, 3, 2, 3])
    with col_date:
        st.text_input("Ngày", key="timeline_date", placeholder="dd/mm/yyyy")
    with col_desc:
        st.text_input("Mô tả", key="timeline_desc", placeholder="Nhập mô tả mốc...")
    with col_notes:
        st.text_area("Ghi chú / Kế hoạch", key="timeline_notes", height=68, placeholder="Ghi chú...")
    with col_actions:
        st.write("")
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
        with btn_col1:
            st.button("➕ Thêm", key="btn_add_milestone", use_container_width=True)
        with btn_col2:
            st.button("🗑️ Xóa mốc", key="btn_del_milestone", use_container_width=True)
        with btn_col3:
            st.button("🗑️ Xóa tất cả", key="btn_del_all", use_container_width=True)
        with btn_col4:
            st.button("🔄 Làm mới", key="btn_refresh", use_container_width=True)
    
    # Progress Summary
    contract_id = st.session_state.contracts_map.get(st.session_state.selected_contract)
    if contract_id:
        files = load_data_from_drive(contract_id)
        aggs = calculate_aggregates(files) if files else {}
    else:
        aggs = {}
    
    cad = aggs.get('CAD', {'TC': 0, 'TT': 0})
    cnc = aggs.get('CNC', {'TC': 0, 'TT': 0})
    van = aggs.get('VAN', {'TC': 0, 'TT': 0})
    vt = aggs.get('VAT_TU', {'TC': 0, 'TT': 0})
    
    st.markdown(f"""
    <div style="background: #1e293b; padding: 8px 16px; border-radius: 8px; margin: 8px 0; font-size: 13px; color: #cbd5e1; font-family: Arial, sans-serif;">
        <span style="margin-right: 24px;"><b>Shop duyệt:</b> {int(cad['TT'])}/{int(cad['TC'])}</span>
        <span style="margin-right: 24px;"><b>Ván:</b> {int(van['TT'])}/{int(van['TC'])}</span>
        <span style="margin-right: 24px;"><b>Sản xuất:</b> {int(cnc['TT'])}/{int(cnc['TC'])}</span>
        <span><b>Vật tư:</b> {int(vt['TT'])}/{int(vt['TC'])}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Timeline with vertical lines
    sample_milestones = [
        {"date": "01/02", "desc": "Bắt đầu", "shop": "0/67", "van": "0/0", "sx": "0/2488", "vt": "0/0"},
        {"date": "05/02", "desc": "Nhập VT đợt 1", "shop": "20/67", "van": "500/4947", "sx": "500/2488", "vt": "100/0"},
        {"date": "10/02", "desc": "Shop duyệt xong", "shop": "67/67", "van": "2000/4947", "sx": "1500/2488", "vt": "200/0"},
        {"date": "15/02", "desc": "Giao hàng", "shop": "67/67", "van": "4947/4947", "sx": "2488/2488", "vt": "0/0"},
    ]
    
    timeline_html = render_timeline_html(sample_milestones)
    components.html(timeline_html, height=200)

# ============================================================
# MATRIX GRID + DETAIL PANEL SECTION
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
        
        .status-done {{ background-color: #1E88E5 !important; color: white; text-align: center; font-weight: 600; }}
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
                    // CAD Row Content
                    row += '<td>' + (cadItems[0].item_name || '') + '</td>';
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
                    // CNC Row Content
                    row += '<td>' + (cncItems[0].item_name || '') + '</td>';
                    row += '<td style="text-align:center;">' + cncQty + '</td>';
                    row += '<td></td>';
                    row += '<td style="text-align:center;">' + (cncItems[0].unit || '') + '</td>';
                    row += '<td style="text-align:center;">' + (cncItems[0].creation_date || '') + '</td>';
                    row += '<td></td><td></td><td></td></tr>';
                    tbody.innerHTML += row;
                }}
                
                for (var i = 0; i < vtPrio.length; i++) {{
                    var d = vtPrio[i];
                    var row = '<tr>';
                    if (firstRow) {{
                        row += '<td class="product-cell" rowspan="' + totalRows + '">' + productCode + '</td>';
                        row += '<td class="product-cell" rowspan="' + totalRows + '" style="font-weight:normal; font-size:12px; width:150px;">' + productNameStr + '</td>';
                        firstRow = false;
                    }}
                    row += '<td>' + (d.item_name || '') + '</td>';
                    row += '<td style="text-align:center;">' + (d.quantity || 0) + '</td>';
                    row += '<td style="text-align:center; font-weight:bold; color:' + (d.remaining < 0 ? '#ef4444' : (d.remaining > 0 ? '#facc15' : '#94a3b8')) + ';">' + (d.remaining || 0) + '</td>';
                    row += '<td style="text-align:center;">' + (d.unit || '') + '</td>';
                    row += '<td style="text-align:center;">' + (d.creation_date || '') + '</td>';
                    row += '<td style="text-align:center;">' + (d.date || '') + '</td>';
                    var sc = d.status_code || '';
                    var statusClass = sc === 'done' ? 'status-done' : (sc === 'missing' ? 'status-missing' : (sc === 'extra' ? 'status-extra' : ''));
                    var statusIcon = sc === 'done' ? '✔' : (sc === 'missing' ? '✖' : (sc === 'extra' ? '➚' : ''));
                    row += '<td class="' + statusClass + '">' + statusIcon + '</td>';
                    row += '<td>' + (d.note || '') + '</td></tr>';
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
                    row += '<td>' + (d.item_name || '') + '</td>';
                    row += '<td style="text-align:center;">' + (d.quantity || 0) + '</td>';
                    row += '<td style="text-align:center; font-weight:bold; color:' + (d.remaining < 0 ? '#ef4444' : (d.remaining > 0 ? '#facc15' : '#94a3b8')) + ';">' + (d.remaining || 0) + '</td>';
                    row += '<td style="text-align:center;">' + (d.unit || '') + '</td>';
                    row += '<td style="text-align:center;">' + (d.creation_date || '') + '</td>';
                    row += '<td style="text-align:center;">' + (d.date || '') + '</td>';
                    var sc = d.status_code || '';
                    var statusClass = sc === 'done' ? 'status-done' : (sc === 'missing' ? 'status-missing' : (sc === 'extra' ? 'status-extra' : ''));
                    var statusIcon = sc === 'done' ? '✔' : (sc === 'missing' ? '✖' : (sc === 'extra' ? '➚' : ''));
                    row += '<td class="' + statusClass + '">' + statusIcon + '</td>';
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
    
    contract_id = st.session_state.contracts_map.get(st.session_state.selected_contract)
    if contract_id:
         files = load_data_from_drive(contract_id)
    else:
         files = []
    
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

