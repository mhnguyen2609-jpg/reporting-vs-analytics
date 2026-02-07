
class Colors:
    """Centralized Color Palette"""
    # Status Colors
    STATUS_DONE = "#1E88E5"     # Blue (Complete/Check)
    STATUS_MISSING = "#FF0000"  # Pure Red (Missing/Cross)
    STATUS_EXTRA = "#CC5500"    # Earthy Orange (Extra/Arrow)
    STATUS_OK_GREEN = "#4CAF50" # Standard Green (Unused currently but good to have)

    # UI Colors
    BACKGROUND_DARK = "#0f172a"
    BACKGROUND_HEADER = "#1e3a5f"
    BACKGROUND_HOVER = "#334155"
    BACKGROUND_SELECTED = "#3b82f6"
    TEXT_PRIMARY = "#cbd5e1"
    TEXT_LIGHT = "#e2e8f0"
    BORDER = "#334155"
    BORDER_LIGHT = "#475569"

    # Category Colors
    CAT_CAD = "#38bdf8"
    CAT_CNC = "#facc15" 
    CAT_VT_UT = "#f472b6"
    CAT_VT = "#a3e635"

class Icons:
    """Centralized Icon Set"""
    STATUS_DONE = "✔"      # Check
    STATUS_MISSING = "✖"   # Cross
    STATUS_EXTRA = "➚"     # Arrow

class Fonts:
    """Standardized Fonts"""
    PRIMARY = "Arial, sans-serif"
    SIZE_SMALL = "10px"
    SIZE_NORMAL = "11px"
    SIZE_HEADER = "12px"
    WEIGHT_BOLD = "600"

class TimelineDesign:
    """Timeline Specific Design Constants"""
    # Dimensions
    PIXELS_PER_DAY = 15
    PADDING_LEFT = 150
    PADDING_RIGHT = 320
    MIN_CARD_WIDTH = 300
    CARD_WIDTH = 220
    
    # Tier Heights (distance from center line)
    TIER_HEIGHTS = [60, 160, 260, 360]
    
    # Type Colors
    TYPE_COLORS = {
        'shop': {'bg': '#ea580c', 'text': '#fff', 'border': '#c2410c'},       # Orange
        'van': {'bg': '#7c3aed', 'text': '#fff', 'border': '#6d28d9'},        # Purple
        'sx': {'bg': '#16a34a', 'text': '#fff', 'border': '#15803d'},         # Green
        'vt': {'bg': '#2563eb', 'text': '#fff', 'border': '#1d4ed8'},         # Blue
        'ke_hoach': {'bg': '#dc2626', 'text': '#fff', 'border': '#b91c1c'},   # Red
        'ghi_chu': {'bg': '#475569', 'text': '#fff', 'border': '#334155'},    # Slate
        'default': {'bg': '#f97316', 'text': '#fff', 'border': '#ea580c'},    # Orange default
    }

class Labels:
    """Centralized UI Text Strings"""
    # Page Config
    PAGE_TITLE = "Dashboard Quản lý Sản xuất (Cloud)"
    PAGE_ICON = "☁️"
    
    # Section Headers
    HEADER_OVERVIEW = "📊 Tổng quan"
    HEADER_DETAILS = "📁 Xem chi tiết"
    HEADER_CONTRACT_PREFIX = "🏗️"
    
    # Input Labels
    LABEL_YEAR = "📅 Chọn Năm"
    LABEL_CONTRACT = "Chọn Hợp đồng"
    OPTION_DEFAULT = "-- Chọn --"
    LABEL_LOCAL_PATH = "Đường dẫn Local"
    
    # Buttons
    BTN_LOAD_PROJECTS = "🔄 Tải tất cả dự án"
    BTN_LOAD_DATA = "🔄 Tải dữ liệu"
    
    # Matrix Table Headers
    MATRIX_HEADERS = ['Mã SP', 'Tên SP', 'CAD', 'ĐẶT HÀNG', 'CNC', 'Vật tư ưu tiên', 'Vật tư']
    
    # Detail Table Headers (HTML)
    DETAIL_HEADERS = [
        "Mã SP", "TÊN SP", "TÊN HÀNG", "SỐ LƯỢNG", 
        "TỒN", "ĐƠN VỊ", "NGÀY LẬP DS", 
        "HOÀN THÀNH", "TRẠNG THÁI", "GHI CHÚ"
    ]
    
    # Master Table Headers
    MASTER_COL_CONTRACT = "Mã hợp đồng_Tên<br>khách hàng"
    MASTER_COL_CATEGORY = "DANH MỤC"
    MASTER_COL_VOLUME = "Khối lượng"
    MASTER_COL_COMPLETE = "Hoàn thành"

def get_status_style_css():
    """Returns CSS blocks for Status Classes"""
    return f"""
        .status-done {{ background-color: {Colors.STATUS_DONE} !important; color: white; text-align: center; font-weight: {Fonts.WEIGHT_BOLD}; }}
        .status-missing {{ background-color: {Colors.STATUS_MISSING} !important; color: white; text-align: center; font-weight: {Fonts.WEIGHT_BOLD}; }}
        .status-extra {{ background-color: {Colors.STATUS_EXTRA} !important; color: white; text-align: center; font-weight: {Fonts.WEIGHT_BOLD}; }}
        .status-ok {{ background-color: {Colors.STATUS_OK_GREEN} !important; color: white; text-align: center; font-weight: {Fonts.WEIGHT_BOLD}; }}
    """

def get_matrix_css(num_groups):
    """Generates the main CSS for the Matrix View"""
    return f"""
        * {{ box-sizing: border-box; font-family: {Fonts.PRIMARY}; }}
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
        
        /* HEADERS */
        .column-header {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            align-items: center;
            background: {Colors.BACKGROUND_HEADER};
            border: 1px solid {Colors.BORDER};
        }}
        
        .column-header span {{
            color: {Colors.TEXT_LIGHT};
            font-size: {Fonts.SIZE_SMALL};
            font-weight: {Fonts.WEIGHT_BOLD};
            text-align: center;
            padding: 3px 2px;
            border-right: 1px solid {Colors.BORDER};
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
        
        /* PRODUCT ROWS */
        .product-row {{
            display: grid;
            grid-template-columns: 90px 220px repeat(5, 32px);
            border: 1px solid {Colors.BORDER};
            align-items: stretch;
            border-top: none;
            background: {Colors.BACKGROUND_DARK};
            color: {Colors.TEXT_PRIMARY};
            font-size: {Fonts.SIZE_NORMAL};
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .product-row:hover {{
            background: {Colors.BACKGROUND_HOVER} !important;
        }}
        
        .product-row.selected {{
            background: {Colors.BACKGROUND_SELECTED} !important;
        }}
        
        .product-row span {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 0;
            padding: 3px 4px;
            color: white;
            font-size: {Fonts.SIZE_NORMAL};
            text-align: center;
            border-right: 1px solid {Colors.BORDER};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
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
            background: linear-gradient(to top right, transparent calc(50% - 1px), {Colors.BORDER_LIGHT}, transparent calc(50% + 1px)),
                        linear-gradient(to top left, transparent calc(50% - 1px), {Colors.BORDER_LIGHT}, transparent calc(50% + 1px)) !important;
        }}
        
        /* DETAIL ROW */
        .detail-row {{
            display: none;
            grid-column: 1 / -1;
            border: 2px solid {Colors.BORDER};
            background: {Colors.BACKGROUND_DARK};
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
            background: {Colors.BACKGROUND_HEADER};
            color: {Colors.TEXT_LIGHT};
            padding: 8px;
            text-align: center;
            font-weight: {Fonts.WEIGHT_BOLD};
            border: 1px solid {Colors.BORDER};
        }}
        
        .detail-table td {{
            padding: 6px 10px;
            border: 1px solid {Colors.BORDER};
            color: {Colors.TEXT_LIGHT};
            background: {Colors.BACKGROUND_DARK};
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
        
        .cat-cad {{ color: {Colors.CAT_CAD}; }}
        .cat-cnc {{ color: {Colors.CAT_CNC}; }}
        .cat-vt-ut {{ color: {Colors.CAT_VT_UT}; }}
        .cat-vt {{ color: {Colors.CAT_VT}; }}
        
        {get_status_style_css()}
        
        .empty-cell {{
            visibility: hidden;
            height: 22px;
        }}
    """
