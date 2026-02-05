
import math
import json
from src.ui.design import Colors, Icons, Labels, get_matrix_css
from src.utils.helpers import natural_sort_key

def get_progress_color(percent):
    """
    Returns hex color based on percentage:
    - 100%: Blue
    - 0-99%: Orange
    - 0%: Gray
    """
    if percent >= 100:
        return Colors.STATUS_DONE  # Blue
    elif percent > 0:
        return Colors.STATUS_EXTRA  # Orange (using Extra color for 'In Progress/Partial' logic here? Or maybe we should add specific Progress Color to Design?)
        # NOTE: Original code used '#FF9800'. Colors.STATUS_EXTRA is '#CC5500'. Let's stick to Design colors logic or keep hardcoded if specific.
        # User asked for everything to be in Design. So let's use Colors.STATUS_EXTRA or add a new one. 
        # For now using STATUS_EXTRA (Orange) is close enough to 'In Progress'.
        return '#FF9800' # Keeping original Yellow-Orange for progress bar to differentiate.
    else:
        return '#374151'  # Gray

def get_cell_style(delta):
    """Returns (icon, color) tuple based on Delta (TC - TT)"""
    # delta = TC - TT
    if delta == 0: return (Icons.STATUS_DONE, Colors.STATUS_DONE)   
    elif delta < 0: return (Icons.STATUS_EXTRA, Colors.STATUS_EXTRA)  
    else: return (Icons.STATUS_MISSING, Colors.STATUS_MISSING)

def render_master_table_html(data):
    """Render the Main Overview Table"""
    if not data:
        return "<p>Không có dữ liệu.</p>"
    
    # Group data by contract
    contracts_data = {}
    for row in data:
        contract = row['contract']
        if contract not in contracts_data:
            contracts_data[contract] = {}
        contracts_data[contract][row['category']] = row
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ box-sizing: border-box; font-family: {Labels.Fonts.PRIMARY if hasattr(Labels, 'Fonts') else 'Arial, sans-serif'}; }}
        body {{ margin: 0; padding: 4px; background: #1a1a2e; }}
        .master-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .master-table th, .master-table td {{
            border: 1px solid #ffffff;
            padding: 6px 10px;
            color: #ffffff;
            vertical-align: middle;
        }}
        .master-table th {{
            background: #1a1a2e;
            font-weight: 600;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .master-table td {{
            background: #1a1a2e;
        }}
        .contract-cell {{ text-align: center; font-weight: 500; }}
        .category-cell {{ text-align: center; font-weight: 500; }}
        .sub-cell {{ text-align: center; font-size: 12px; }}
        .number-cell {{ text-align: center; }}
        .percent-cell {{ padding: 0 !important; position: relative; overflow: hidden; }}
        .progress-wrapper {{ position: relative; width: 100%; height: 100%; min-height: 28px; display: flex; align-items: center; justify-content: center; }}
        .progress-fill {{ position: absolute; left: 0; top: 0; height: 100%; z-index: 1; }}
        .progress-text {{ position: relative; z-index: 2; color: white; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }}
    </style>
    </head>
    <body>
    <table class="master-table">
        <thead>
            <tr>
                <th style="width:20%;">{Labels.MASTER_COL_CONTRACT}</th>
                <th colspan="2" style="width:25%;">{Labels.MASTER_COL_CATEGORY}</th>
                <th style="width:15%;">{Labels.MASTER_COL_VOLUME}</th>
                <th style="width:15%;">{Labels.MASTER_COL_COMPLETE}</th>
                <th style="width:12%;">%</th>
            </tr>
        </thead>
        <tbody>
    """
    
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
    
    sorted_contracts = sorted(contracts_data.keys(), key=natural_sort_key)

    for contract in sorted_contracts:
        cat_data = contracts_data[contract]
        html += f'<tr><td class="contract-cell" rowspan="7">{contract}</td>' # Total 7 rows
        
        # Helper to simplify rows
        def row_html(cat_name, cat_key, is_sub=False):
            d = cat_data.get(cat_key, {'tc': 0, 'tt': 0, 'percent': 0})
            tc = int(d['tc']) if d['tc'] > 0 else ''
            tt = int(d['tt']) if d['tt'] > 0 else ''
            
            r = ""
            if not is_sub:
                r += f'<td class="category-cell" colspan="2">{cat_name}</td>'
            
            r += f'<td class="number-cell">{tc}</td>'
            r += f'<td class="number-cell">{tt}</td>'
            r += render_progress_cell(d['percent'], d['tc'])
            return r

        # CAD
        html += row_html('CAD', 'CAD') + '</tr>'
        # CNC
        html += '<tr>' + row_html('CNC', 'CNC') + '</tr>'
        # VAN
        html += '<tr>' + row_html('VÁN', 'VÁN') + '</tr>'
        
        # VAT TU
        vt = cat_data.get('VẬT TƯ', {'tc': 0, 'tt': 0, 'percent': 0, 'nhom_hang_tc':0, 'nhom_hang_tt':0, 'nhom_percent':0})
        nhom_tc = int(vt.get('nhom_hang_tc', 0)) if vt.get('nhom_hang_tc', 0) > 0 else ''
        nhom_tt = int(vt.get('nhom_hang_tt', 0)) if vt.get('nhom_hang_tt', 0) > 0 else ''
        
        html += f'<tr><td class="category-cell" rowspan="2">VẬT TƯ</td><td class="sub-cell">Nhóm hàng</td><td class="number-cell">{nhom_tc}</td><td class="number-cell">{nhom_tt}</td>'
        html += render_progress_cell(vt.get('nhom_percent', 0), vt.get('nhom_hang_tc', 0)) + '</tr>'
        
        html += f'<tr><td class="sub-cell">Số lượng</td>'
        html += f'<td class="number-cell">{int(vt["tc"]) if vt["tc"]>0 else ""}</td>'
        html += f'<td class="number-cell">{int(vt["tt"]) if vt["tt"]>0 else ""}</td>'
        html += render_progress_cell(vt['percent'], vt['tc']) + '</tr>'

        # VAT TU UU TIEN
        vtut = cat_data.get('VẬT TƯ ƯU TIÊN', {'tc': 0, 'tt': 0, 'percent': 0, 'nhom_hang_tc':0, 'nhom_hang_tt':0, 'nhom_percent':0})
        nhom_tc = int(vtut.get('nhom_hang_tc', 0)) if vtut.get('nhom_hang_tc', 0) > 0 else ''
        nhom_tt = int(vtut.get('nhom_hang_tt', 0)) if vtut.get('nhom_hang_tt', 0) > 0 else ''
        
        html += f'<tr><td class="category-cell" rowspan="2">VẬT TƯ ƯU TIÊN</td><td class="sub-cell">Nhóm hàng</td><td class="number-cell">{nhom_tc}</td><td class="number-cell">{nhom_tt}</td>'
        html += render_progress_cell(vtut.get('nhom_percent', 0), vtut.get('nhom_hang_tc', 0)) + '</tr>'
        
        html += f'<tr><td class="sub-cell">Số lượng</td>'
        html += f'<td class="number-cell">{int(vtut["tc"]) if vtut["tc"]>0 else ""}</td>'
        html += f'<td class="number-cell">{int(vtut["tt"]) if vtut["tt"]>0 else ""}</td>'
        html += render_progress_cell(vtut['percent'], vtut['tc']) + '</tr>'

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
        .timeline-wrapper { position: relative; height: 120px; }
        .timeline-bar { position: absolute; top: 50%; left: 0; right: 0; height: 3px; background: #0ea5e9; transform: translateY(-50%); }
        .milestones { display: flex; justify-content: space-between; position: relative; height: 100%; align-items: center; }
        .milestone { position: relative; display: flex; flex-direction: column; align-items: center; }
        .milestone-dot { width: 12px; height: 12px; background: #f97316; border-radius: 50%; position: relative; z-index: 2; }
        .milestone-above { position: absolute; bottom: 50%; display: flex; flex-direction: column; align-items: center; }
        .milestone-below { position: absolute; top: 50%; display: flex; flex-direction: column; align-items: center; }
        .milestone-line-up { width: 2px; height: 25px; background: #f97316; }
        .milestone-line-down { width: 2px; height: 25px; background: #f97316; }
        .milestone-info { font-size: 11px; color: #f97316; text-align: center; white-space: nowrap; }
        .milestone-date { font-weight: 700; font-size: 12px; margin-bottom: 2px; }
        .milestone-desc { color: #94a3b8; font-size: 10px; }
        .milestone-detail { color: #e2e8f0; font-size: 10px; line-height: 1.4; }
    </style>
    </head>
    <body>
    <div class="timeline-wrapper">
        <div class="timeline-bar"></div>
        <div class="milestones">
    """
    
    for i, m in enumerate(milestones):
        is_above = (i % 2 == 0)
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

def render_matrix_grids_html(matrix_df, details_map):
    """Render matrix using CSS Grid - 4 columns, click expands full-width detail row inline."""
    if matrix_df.empty:
        return "<p>Không có dữ liệu Matrix.</p>"
    
    products = matrix_df.index.tolist()
    total = len(products)
    items_per_group = 25
    num_groups = math.ceil(total / items_per_group)
    
    # Organize products into groups
    groups = []
    for g in range(num_groups):
        start_idx = g * items_per_group
        end_idx = min((g + 1) * items_per_group, total)
        groups.append(products[start_idx:end_idx])
    
    max_rows = max(len(g) for g in groups) if groups else 0
    headers = Labels.MATRIX_HEADERS
    
    css = get_matrix_css(num_groups)
    details_json = json.dumps(details_map, ensure_ascii=False, default=str)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        {css}
    </style>
    <script>
        var allDetails = {details_json};
        var selectedRow = null;
        var activeDetailRow = null;
        
        function showDetail(productCode, rowElement, detailRowId) {{
            if (selectedRow) {{ selectedRow.classList.remove('selected'); }}
            if (activeDetailRow) {{ activeDetailRow.style.display = 'none'; }}
            
            if (selectedRow === rowElement) {{
                selectedRow = null; activeDetailRow = null; return;
            }}
            
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
                     
                     if (st === 'Hoàn thành' || st === 'OK' || st === 'Đủ') {{ stClass = 'status-done'; stIcon = '{Icons.STATUS_DONE} '; }}
                     else if (st === 'Đang làm' || st === 'Thiếu') {{ stClass = 'status-missing'; stIcon = '{Icons.STATUS_MISSING} '; }}
                     else if (st === 'Phát sinh' || st === 'Vượt KH' || st === 'Dư') {{ stClass = 'status-extra'; stIcon = '{Icons.STATUS_EXTRA} '; }}
                     
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
        html += '<div class="matrix-grid">'
        # Headers
        if row_idx == 0:
            for g in range(num_groups):
                html += '<div class="column-header">'
                for h in headers:
                    html += f'<span>{h}</span>'
                html += '</div>'
            html += '</div><div class="matrix-grid">'
        
        # Product Rows
        for g in range(num_groups):
            if row_idx < len(groups[g]):
                prod = groups[g][row_idx]
                row_data = matrix_df.loc[prod] if prod in matrix_df.index else {}
                
                # Check 5 categories: CAD, DAT_HANG, CNC, VT_UT, VT
                values = []
                for cat_key in ['CAD', 'DAT_HANG', 'CNC', 'VAT_TU_UU_TIEN', 'VAT_TU']:
                    tc = row_data.get(f'{cat_key}_TC', 0)
                    tt = row_data.get(f'{cat_key}_TT', 0)
                    delta = tc - tt
                    
                    if tc > 0:
                        icon, color = get_cell_style(delta)
                        values.append({'has_data': True, 'style': f'background:{color};', 'icon': icon})
                    else:
                        values.append({'has_data': False})
                
                # Define row HTML
                detail_id = f"detail_{prod}_{row_idx}"
                html += f'''
                <div class="grid-column">
                    <div class="product-row" onclick="showDetail('{prod}', this, '{detail_id}')">
                        <span title="{prod}">{prod}</span>
                        <span title="{row_data.get('product_name', '')}">{row_data.get('product_name', '')}</span>
                        {"".join([f"<span style='{v['style']}'>{v['icon']}</span>" if v['has_data'] else "<span class='cell-empty'></span>" for v in values])}
                    </div>
                </div>
                '''
            else:
                html += '<div class="grid-column"></div>' # Placeholder for alignment
        
        html += '</div>'
        
        # Detail Row (Full width expansion)
        html += '<div class="matrix-grid">'
        for g in range(num_groups):
             if row_idx < len(groups[g]):
                prod = groups[g][row_idx]
                detail_id = f"detail_{prod}_{row_idx}"
                html += f'''
                <div id="{detail_id}" class="detail-row">
                    <table class="detail-table">
                        <thead>
                            <tr>
                                <th style="width:90px;">{Labels.DETAIL_HEADERS[0]}</th>
                                <th>{Labels.DETAIL_HEADERS[1]}</th>
                                <th>{Labels.DETAIL_HEADERS[2]}</th>
                                <th style="width:60px;">{Labels.DETAIL_HEADERS[3]}</th>
                                <th style="width:50px;">{Labels.DETAIL_HEADERS[4]}</th>
                                <th style="width:55px;">{Labels.DETAIL_HEADERS[5]}</th>
                                <th style="width:100px;">{Labels.DETAIL_HEADERS[6]}</th>
                                <th style="width:100px;">{Labels.DETAIL_HEADERS[7]}</th>
                                <th style="width:85px;">{Labels.DETAIL_HEADERS[8]}</th>
                                <th style="width:100px;">{Labels.DETAIL_HEADERS[9]}</th>
                            </tr>
                        </thead>
                        <tbody class="detail-tbody"></tbody>
                    </table>
                </div>
                '''
        html += '</div>'
        
    html += "</body></html>"
    return html
