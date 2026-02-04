import pandas as pd
import os
import io
from typing import Optional, Dict, Tuple, Union, Any

def find_header_row(file_input: Union[str, io.BytesIO], max_rows: int = 20) -> int:
    """
    Finds the row number containing the actual header by looking for key columns.
    Returns the 0-indexed row number, or 0 if not found.
    """
    # Reset stream if bytes
    if hasattr(file_input, 'seek'):
        file_input.seek(0)

    # Read first N rows without header
    try:
        df_raw = pd.read_excel(file_input, header=None, nrows=max_rows)
    except:
        return 0
    
    # Keywords that indicate a header row
    header_keywords = ['số lượng', 'tên hàng', 'mã sp', 'mã hiệu', 'stt', 'khối lượng']
    
    for idx, row in df_raw.iterrows():
        # Convert row to lowercase strings
        row_values = [str(v).lower().strip() for v in row.values if pd.notna(v)]
        # Check if any header keyword is in this row
        matches = sum(1 for kw in header_keywords if any(kw in val for val in row_values))
        if matches >= 2:  # At least 2 keywords found -> likely header
            return idx
    
    return 0  # Default to first row


def normalize_columns(columns: pd.Index) -> Dict[str, str]:
    """
    Creates a mapping from actual column names to standardized keys.
    Standard Keys: 'key' (Identifier), 'quantity' (Số lượng), 'don_vi' (Đơn vị)
    """
    mapping = {}
    for col in columns:
        col_lower = str(col).lower().strip()
        # Quantity column
        if any(kw in col_lower for kw in ['số lượng', 'sl', 'quantity', 'soluong', 'khối lượng']):
            mapping[col] = 'quantity'
        
        # Unit column (Đơn vị)
        elif any(kw in col_lower for kw in ['đơn vị', 'don vi', 'unit', 'dvt']):
            mapping[col] = 'don_vi'
        
        # Identifier column candidates
        elif any(kw in col_lower for kw in ['mã sp', 'mã sản phẩm', 'model', 'product code', 'key']):
            mapping[col] = 'ma_sp'
        elif any(kw in col_lower for kw in ['tên hàng', 'tên vật tư', 'tên sản phẩm', 'item name']):
            mapping[col] = 'ten_hang'
        elif any(kw in col_lower for kw in ['mã hiệu (unique)', 'unique code']):
            mapping[col] = 'ma_hieu_unique'
        elif any(kw in col_lower for kw in ['mã hiệu', 'ký hiệu', 'code']):
            mapping[col] = 'ma_hieu'
            
    return mapping


def read_cell_c8(file_input: Union[str, io.BytesIO]) -> str:
    """
    Reads cell C8 from Excel file (creation date / ngày lập danh sách).
    C8 = Row 8 (1-indexed) = Row 7 (0-indexed), Column C = Column 2 (0-indexed).
    """
    try:
        # Reset stream if bytes
        if hasattr(file_input, 'seek'):
            file_input.seek(0)
            
        df_raw = pd.read_excel(file_input, header=None, nrows=10)
        if df_raw.shape[0] > 7 and df_raw.shape[1] > 2:
            value = df_raw.iloc[7, 2]  # Row 8, Col C
            if pd.notna(value):
                # Try to format as date if it's a datetime
                if hasattr(value, 'strftime'):
                    return value.strftime('%d/%m/%Y')
                return str(value).strip()
    except:
        pass
    return ''


def read_excel_data(file_input: Union[str, bytes], source_type: str) -> Optional[pd.DataFrame]:
    """
    Reads an Excel file and prepares it for calculation.
    Automatically detects header row.
    
    Args:
        file_input: Absolute path to the file OR bytes content.
        source_type: The type of file (e.g., 'SHOP_TC', 'VT_NHAP').
    
    Returns:
        DataFrame with standardized columns ['key', 'quantity', ...] or None if error.
    """
    try:
        source = None
        file_path_str = ''
        
        if isinstance(file_input, str):
            if not os.path.exists(file_input):
                 return None
            source = file_input
            file_path_str = file_input
        else:
            source = io.BytesIO(file_input)
            file_path_str = 'memory'

        # Step 1: Find the actual header row
        header_row = find_header_row(source)
        
        # Step 2: Read with correct header
        if hasattr(source, 'seek'): source.seek(0)
        df = pd.read_excel(source, header=header_row)
        
        # Standardize columns
        mapping = normalize_columns(df.columns)
        df_renamed = df.rename(columns=mapping)
        
        # Handle duplicate columns (keep first occurrence)
        df_renamed = df_renamed.loc[:, ~df_renamed.columns.duplicated()]
        
        # Determine which column is the 'key' based on source_type
        # Rules from ref_ui_project_overview.md
        key_col = None
        
        if 'SHOP' in source_type:
             key_col = 'ma_sp' # CAD (Shop) -> Mã SP
        elif 'VAN' in source_type:
            key_col = 'ma_hieu' # VÁN -> Mã hiệu
        elif 'NESTING' in source_type or 'CAT' in source_type:
            # CNC: ưu tiên dùng ma_sp nếu có
            if 'ma_sp' in df_renamed.columns:
                key_col = 'ma_sp'
            else:
                key_col = 'ten_hang'
        else:
            # VT (Ưu tiên & Thường) -> Ưu tiên Mã SP, fallback Tên hàng
            if 'ma_sp' in df_renamed.columns:
                key_col = 'ma_sp'
            else:
                key_col = 'ten_hang'
            
        if key_col not in df_renamed.columns:
            # Fallback: try to find any key column
            for possible_key in ['ma_sp', 'ten_hang', 'ma_hieu']:
                if possible_key in df_renamed.columns:
                    key_col = possible_key
                    break
        
        if key_col and key_col in df_renamed.columns:
             df_renamed['key'] = df_renamed[key_col]
        else:
            # No key found, skip this file
            return None

        # Ensure 'quantity' exists
        if 'quantity' not in df_renamed.columns:
             return None  # Can't calculate without quantity
        
        # Force quantity to numeric
        df_renamed['quantity'] = pd.to_numeric(df_renamed['quantity'], errors='coerce').fillna(0)
        
        # For SHOP files: default quantity to 1 when empty/0 (each row = 1 product)
        if 'SHOP' in source_type:
            df_renamed.loc[df_renamed['quantity'] == 0, 'quantity'] = 1
        
        # Clean key
        if 'key' in df_renamed.columns:
            df_renamed['key'] = df_renamed['key'].astype(str).str.strip()
            # Remove empty keys
            df_renamed = df_renamed[df_renamed['key'] != 'nan']
            df_renamed = df_renamed[df_renamed['key'] != '']
            df_renamed = df_renamed[df_renamed['key'].notna()]
        
        # Add file metadata as columns
        df_renamed['_file_path'] = file_path_str
        df_renamed['_source_type'] = source_type
        
        # Read C8
        if hasattr(source, 'seek'): source.seek(0)
        df_renamed['_creation_date'] = read_cell_c8(source)
            
        return df_renamed
        
    except Exception as e:
        # print(f"Error reading {file_input}: {e}")
        return None
