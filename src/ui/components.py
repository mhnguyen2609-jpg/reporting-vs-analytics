
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
        body {{ margin: 0; padding: 4px; background: transparent; }}
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
            white-space: nowrap;
        }}
        .master-table th {{
            background: transparent;
            font-weight: 600;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .master-table td {{
            background: transparent;
        }}
        .contract-cell {{ text-align: center; font-weight: 500; }}
        .category-cell {{ text-align: center; font-weight: 500; }}
        .sub-cell {{ text-align: center; font-size: 12px; }}
        .number-cell {{ text-align: center; }}
        .percent-cell {{ text-align: center; }}
        .progress-text {{ color: white; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }}
    </style>
    </head>
    <body>
    <div style="overflow-x: auto; width: 100%;">
    <table class="master-table">
        <thead>
            <tr>
                <th>{Labels.MASTER_COL_CONTRACT}</th>
                <th colspan="2">{Labels.MASTER_COL_CATEGORY}</th>
                <th>{Labels.MASTER_COL_VOLUME}</th>
                <th>{Labels.MASTER_COL_COMPLETE}</th>
                <th>%</th>
            </tr>
        </thead>
        <tbody>
    """
    
    def render_progress_cell(percent, tc):
        if tc > 0:
            color = get_progress_color(percent)
            pct_val = min(percent, 100)
            bg_style = f"background: linear-gradient(90deg, {color} {pct_val}%, transparent {pct_val}%);"
            return f'<td class="percent-cell" style="{bg_style}"><span class="progress-text">{percent:.1f}%</span></td>'
        return '<td class="percent-cell"></td>'
    
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

    html += "</tbody></table></div></body></html>"
    return html

def render_timeline_html(milestones):
    """Render multi-tier color-coded timeline with card-style info boxes."""
    if not milestones: return ""
    
    from datetime import datetime
    
    from src.ui.design import Colors, Icons, Labels, TimelineDesign, get_matrix_css
    
    # Color mapping for milestone types
    TYPE_COLORS = TimelineDesign.TYPE_COLORS
    
    # 1. Parse Dates
    parsed_ms = []
    valid_dates = []
    
    for m in milestones:
        d_str = m.get('full_date', m.get('date'))
        dt = None
        try:
            dt = datetime.strptime(d_str, "%Y-%m-%d")
        except:
            try:
                dt = datetime.strptime(d_str, "%d/%m/%Y")
            except:
                pass
        
        if dt:
            # Determine type from desc
            desc = m.get('desc', '').lower()
            m_type = 'default'
            if 'shop' in desc: m_type = 'shop'
            elif 'ván' in desc or 'van' in desc: m_type = 'van'
            elif 'sản xuất' in desc or 'sx' in desc or 'cnc' in desc: m_type = 'sx'
            elif 'vật tư' in desc or 'vt:' in desc: m_type = 'vt'
            elif 'kế hoạch' in desc: m_type = 'ke_hoach'
            elif 'ghi chú' in desc: m_type = 'ghi_chu'
            
            parsed_ms.append({**m, '_dt': dt, '_type': m_type})
            valid_dates.append(dt)
    
    if not valid_dates: return "<p>Không thể hiển thị Timeline.</p>"
    
    min_date = min(valid_dates)
    max_date = max(valid_dates)
    total_days = (max_date - min_date).days
    
    # 2. Width Calculation
    dataset_span = max(1, total_days)
    pixels_per_day = TimelineDesign.PIXELS_PER_DAY
    min_width_for_milestones = len(milestones) * TimelineDesign.MIN_CARD_WIDTH
    bar_width = max(600, dataset_span * pixels_per_day, min_width_for_milestones)
    
    padding_left = TimelineDesign.PADDING_LEFT
    padding_right = TimelineDesign.PADDING_RIGHT
    total_width = padding_left + bar_width + padding_right
    
    # Tier heights
    TIER_HEIGHTS = TimelineDesign.TIER_HEIGHTS
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }}
        body {{ margin: 0; padding: 20px 0; background: transparent; overflow-x: auto; }}
        
        .timeline-wrapper {{
            width: {total_width}px;
            min-height: 600px;
            position: relative;
        }}
        
        .timeline-bar {{
            position: absolute;
            top: 50%;
            left: {padding_left}px;
            width: {bar_width}px;
            height: 6px;
            background: linear-gradient(90deg, #0ea5e9, #06b6d4);
            transform: translateY(-50%);
            border-radius: 3px;
            z-index: 1;
        }}
        
        .milestone {{
            position: absolute;
            top: 50%;
            z-index: 10;
        }}
        
        .milestone-dot {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: 3px solid #0f172a;
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            z-index: 15;
            transition: all 0.3s ease;
        }}

        .milestone-dot.diamond {{
            border-radius: 2px;
            transform: translate(-50%, -50%) rotate(45deg);
        }}
        
        .milestone-dot.star {{
            border: none;
            width: 22px; 
            height: 22px;
            clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
            background-color: #dc2626; /* Fallback */
        }}

        .milestone-dot.square {{
            border-radius: 0;
            width: 14px;
            height: 14px;
        }}
        
        .milestone-line {{
            position: absolute;
            width: 2px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 5;
        }}
        
        .milestone-card {{
            position: absolute;
            width: 220px;
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            z-index: 20;
            left: 0;  /* Align card to start from dot position */
        }}
        
        .card-date {{
            font-weight: 700;
            font-size: 14px;
            margin-bottom: 4px;
        }}
        
        .card-desc {{
            font-size: 11px;
            line-height: 1.4;
            white-space: pre-wrap;
            opacity: 0.95;
        }}
        
        .card-details {{
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid rgba(255,255,255,0.2);
            font-size: 10px;
            opacity: 0.85;
        }}
        
        /* Legend */
        .legend {{
            position: fixed;
            top: 20px;
            left: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 0; /* Remove padding */
            background: transparent; /* Transparent background */
            border: none; /* No border */
            border-radius: 0;
            font-size: 13px; /* Slightly larger text */
            color: #e2e8f0;
            z-index: 1000;
            box-shadow: none; /* No shadow */
            min-width: 140px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}
        .legend-dot.diamond {{ border-radius: 1px; transform: rotate(45deg); }}
        .legend-dot.star {{ 
            width: 12px; height: 12px; border-radius: 0; 
            clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%); 
        }}
        .legend-dot.square {{ border-radius: 0; }}
    </style>
    </head>
    <body>
    <div class="timeline-wrapper">
        <div class="timeline-bar"></div>
    """
    
    sorted_ms = sorted(parsed_ms, key=lambda x: x['_dt'])
    
    # Tier assignment algorithm - prevent overlap
    # Track occupied positions: {tier: [(left_x, right_x), ...]}
    tier_occupied = {0: [], 1: [], 2: [], 3: []}  # 0,1 = above; 2,3 = below
    
    for i, m in enumerate(sorted_ms):
        # Position calculation
        if total_days > 0:
            days_from_start = (m['_dt'] - min_date).days
            position_px = padding_left + (days_from_start / total_days) * bar_width
        else:
            position_px = padding_left + (i / max(1, len(sorted_ms)-1)) * bar_width if len(sorted_ms) > 1 else padding_left + bar_width/2
        
        card_width = 220
        # Cards are now left-aligned (start at dot position, extend right)
        card_left = position_px
        card_right = position_px + card_width
        
        # Find best tier (alternate above/below, then find non-overlapping tier)
        prefer_above = (i % 2 == 0)
        
        def find_tier(is_above):
            tiers = [0, 1] if is_above else [2, 3]
            for t in tiers:
                overlap = False
                for (l, r) in tier_occupied[t]:
                    if not (card_right < l - 20 or card_left > r + 20):
                        overlap = True
                        break
                if not overlap:
                    return t
            return tiers[-1]  # Fallback to furthest tier
        
        tier = find_tier(prefer_above)
        if tier is None:
            tier = find_tier(not prefer_above)  # Try other side
        
        tier_occupied[tier].append((card_left, card_right))
        
        is_above = tier < 2
        tier_level = tier if tier < 2 else tier - 2
        height = TIER_HEIGHTS[tier_level]
        
        # Colors
        colors = TYPE_COLORS.get(m['_type'], TYPE_COLORS['default'])
        
        # Shape
        shape_class = "circle"
        # Check for aggregate data keys
        if any(k in m for k in ['shop', 'van', 'sx', 'vt']):
            shape_class = "square"
        elif m['_type'] == 'ke_hoach': 
            shape_class = "star"
        elif m['_type'] == 'ghi_chu': 
            shape_class = "diamond"

        # Build card content
        details_html = ""
        if 'shop' in m: details_html += f'Shop: {m["shop"]} | '
        if 'van' in m: details_html += f'Ván: {m["van"]} | '
        if 'sx' in m: details_html += f'SX: {m["sx"]} | '
        if 'vt' in m: details_html += f'VT: {m["vt"]} | '
        details_html = details_html.rstrip(' | ')
        
        desc_html = m.get('desc', '') or ''
        
        # Card positioning
        if is_above:
            card_style = f"bottom: {height}px;"
            line_style = f"bottom: 0; height: {height - 8}px; background: {colors['border']};"
        else:
            card_style = f"top: {height}px;"
            line_style = f"top: 0; height: {height - 8}px; background: {colors['border']};"
        
        html += f"""
        <div class="milestone" style="left: {position_px}px;">
            <div class="milestone-dot {shape_class}" style="background: {colors['bg']};"></div>
            <div class="milestone-line" style="{line_style}"></div>
            <div class="milestone-card" style="{card_style} background: {colors['bg']}; border: 2px solid {colors['border']}; color: {colors['text']};">
                <div class="card-date">{m['date']}</div>
                <div class="card-desc">{desc_html}</div>
                {'<div class="card-details">' + details_html + '</div>' if details_html else ''}
            </div>
        </div>
        """
    
    # Legend
    html += """
    </div>
    <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:#ea580c;"></div>Shop</div>
        <div class="legend-item"><div class="legend-dot" style="background:#7c3aed;"></div>Ván</div>
        <div class="legend-item"><div class="legend-dot" style="background:#16a34a;"></div>Sản xuất</div>
        <div class="legend-item"><div class="legend-dot" style="background:#2563eb;"></div>Vật tư</div>
        <div class="legend-item"><div class="legend-dot star" style="background:#dc2626;"></div>Kế hoạch</div>
        <div class="legend-item"><div class="legend-dot diamond" style="background:#475569;"></div>Ghi chú</div>
        <div class="legend-item"><div class="legend-dot square" style="border: 2px solid #fff; background: transparent;"></div>Tổng hợp</div>
    </div>
    </body></html>
    """
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
                     
                     if (st === 'Hoàn thành' || st === 'Đủ') {{ stClass = 'status-done'; stIcon = '✔ '; }}
                     else if (st === 'Thiếu' || st === 'Đang làm') {{ stClass = 'status-missing'; stIcon = '✖ '; }}
                     else if (st === 'Phát sinh' || st === 'Vượt KH' || st === 'Dư') {{ stClass = 'status-extra'; stIcon = '➚ '; }}
                     
                     row += '<td style="text-align:center;">' + (d.date || d.creation_date || '') + '</td>';
                     row += '<td class="' + stClass + '" style="white-space: nowrap;">' + stIcon + st + '</td>'; 
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
                        <span title="{row_data.get('TEN_SP', '')}">{row_data.get('TEN_SP', '')}</span>
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

def render_material_stats_html(df):
    """Renders the Material Statistics table (Thống kê vật tư)."""
    if df.empty:
        return "<p style='color:white; text-align:center;'>Không có dữ liệu thống kê vật tư.</p>"
        
    css = f"""
    <style>
        .mat-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            color: #e2e8f0;
            font-family: Arial, sans-serif;
        }}
        .mat-table th {{
            background: transparent;
            border: 1px solid #334155;
            padding: 8px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .mat-table td {{
            border: 1px solid #334155;
            padding: 8px 12px;
            vertical-align: middle;
            background: transparent;
        }}
        .mat-table tr:hover td {{
            background: rgba(255,255,255,0.05);
        }}
        .col-stt {{ width: 40px; text-align: center; }}
        .col-qty {{ width: 70px; text-align: center; }}
        .col-unit {{ width: 60px; text-align: center; }}
        .col-rem {{ width: 70px; text-align: center; }}
        .col-status {{ width: 120px; text-align: center; white-space: nowrap; }}
        
        /* Status styles for full cell fill */
        .status-done {{ background-color: #1E88E5 !important; color: white; font-weight: bold; }}
        .status-missing {{ background-color: #FF0000 !important; color: white; font-weight: bold; }}
        .status-extra {{ background-color: #CC5500 !important; color: white; font-weight: bold; }}
    </style>
    """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{css}</head>
    <body>
    <div style="max-height: 1500px; overflow-y: auto;">
        <table class="mat-table">
            <thead>
                <tr>
                    <th class="col-stt">STT</th>
                    <th>Tên hàng</th>
                    <th class="col-qty">Số lượng</th>
                    <th class="col-rem">Tồn</th>
                    <th class="col-unit">Đơn vị</th>
                    <th>Mã SP - Tên SP</th>
                    <th class="col-status">Trạng thái</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for idx, row in df.iterrows():
        related_products = row['Mã SP - Tên SP']
        related_html = ""
        if isinstance(related_products, list):
            related_html = "".join([f"<div style='padding:2px 0;'>{p}</div>" for p in related_products])
        else:
            related_html = str(related_products)
            
        st = row.get('Trạng thái', '')
        stClass = ''
        stIcon = ''
        if st == 'Hoàn thành' : stClass = 'status-done'; stIcon = '✔'
        elif st == 'Thiếu' : stClass = 'status-missing'; stIcon = '✖'
        elif st == 'Phát sinh' : stClass = 'status-extra'; stIcon = '➚'
            
        html += f"""
        <tr>
            <td class="col-stt">{idx + 1}</td>
            <td style="font-weight: 500;">{row['Tên hàng']}</td>
            <td class="col-qty">{row['Số lượng']}</td>
            <td class="col-rem">{row['Tồn']}</td>
            <td class="col-unit">{row['Đơn vị']}</td>
            <td>{related_html}</td>
            <td class="col-status {stClass}">{stIcon} {st}</td>
        </tr>
        """
        
    html += """
            </tbody>
        </table>
    </div>
    </body>
    </html>
    """
    return html
