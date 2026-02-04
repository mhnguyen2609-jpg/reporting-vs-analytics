import os
import pandas as pd
from typing import Dict, Any, Optional

def load_project_identity(config_path: str) -> Dict[str, Any]:
    """
    Reads the config.xlsx file to extract project identity (Contract Code, Customer Name)
    and Timeline milestones.
    
    Args:
        config_path: Absolute path to the config.xlsx file.
        
    Returns:
        Dictionary containing:
        {
            'contract_code': str,
            'customer_name': str,
            'timeline_date': datetime or None (from cell C8),
            'errors': list of error messages
        }
    """
    result = {
        'contract_code': None,
        'customer_name': None,
        'timeline_date': None,
        'errors': []
    }
    
    if not os.path.exists(config_path):
        result['errors'].append("File config.xlsx not found.")
        return result
        
    try:
        # Read the first sheet for Project Info
        # We need to find columns "Mã hợp đồng" and "Tên khách hàng"
        # Since we don't know the exact row, we read the first few rows (e.g. 5) as header is likely there.
        # But commonly read_excel takes header=0. Let's try reading and finding columns.
        df = pd.read_excel(config_path, header=0)
        
        # Normalize column names to lower case or strip to find matches
        cols = {c.strip().lower(): c for c in df.columns}
        
        # Find Contract Code
        ma_hd_col = None
        for c in cols:
            if "mã hợp đồng" in c:
                ma_hd_col = cols[c]
                break
        
        # Find Customer Name
        ten_kh_col = None
        for c in cols:
            if "tên khách hàng" in c:
                ten_kh_col = cols[c]
                break
        
        if ma_hd_col and not df.empty:
            result['contract_code'] = str(df.iloc[0][ma_hd_col]).strip()
        else:
            result['errors'].append("Column 'Mã hợp đồng' not found or empty.")
            
        if ten_kh_col and not df.empty:
            result['customer_name'] = str(df.iloc[0][ten_kh_col]).strip()
        else:
            result['errors'].append("Column 'Tên khách hàng' not found or empty.")
            
        # Read Timeline Date from Cell C8
        # C8 corresponds to Row 7 (0-indexed) and Column 2 (0-indexed 'C').
        # We need to re-read without header to access by coordinate safely.
        df_raw = pd.read_excel(config_path, header=None)
        if df_raw.shape[0] > 7 and df_raw.shape[1] > 2:
            result['timeline_date'] = df_raw.iloc[7, 2] # Row 8, Col C
        
    except Exception as e:
        result['errors'].append(f"Error reading config.xlsx: {str(e)}")
        
    return result
