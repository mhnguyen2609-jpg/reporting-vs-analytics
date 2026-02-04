import os
from typing import List, Dict, Optional
from src.core.constants import DEFAULT_ROOT_PATH, NamingKeywords, EXCEL_EXTENSIONS

def identify_source_type(filename: str, folder_name: str = None) -> Optional[str]:
    """
    Identifies the source type based on the filename using keywords defined in constants.py.
    Prioritizes longer keywords/more specific matches.
    Also considers folder name for context-aware identification.
    """
    filename_upper = filename.upper()
    folder_upper = folder_name.upper() if folder_name else ""
    
    # Sort keywords by length in descending order to match longest first (e.g. DMVTN-VAN before DMVTN)
    # We flatten the dictionary to a list of (type, keyword) tuples
    all_keywords = []
    for type_name, keywords in NamingKeywords.items():
        for keyword in keywords:
            all_keywords.append((type_name, keyword))
    
    # Sort by keyword length desc
    all_keywords.sort(key=lambda x: len(x[1]), reverse=True)
    
    match = None
    for type_name, keyword in all_keywords:
        if keyword in filename_upper:
            match = type_name
            break
            
    # Apply Overrides based on Folder/Prefix context
    if match:
        # If match is VT_NHAP (DMVTN) but folder is XUAT or prefix is TC -> Override to VT_XUAT
        if match == 'VT_NHAP':
             if folder_upper == 'XUAT' or filename_upper.startswith('TC'):
                 return 'VT_XUAT'
    
    return match

def scan_project_files(root_path: str = DEFAULT_ROOT_PATH, year: str = None, contract_id: str = None) -> List[Dict]:
    """
    Scans for Excel files in the specified project directory.
    
    Args:
        root_path: The base directory to scan (default: D:\Cong viec).
        year: Optional filter by year folder.
        contract_id: Optional filter for contract folder.
        
    Returns:
        List of dictionaries containing file metadata:
        {
            'path': absolute path,
            'filename': filename,
            'source_type': identified type or None
        }
    """
    # 1. Determine the starting directory
    start_dir = root_path
    if year:
        start_dir = os.path.join(start_dir, str(year))
        if contract_id:
            # This is a fuzzy search since contract folders are like "STT. ContractID_Name"
            # We need to find the specific folder.
            if os.path.exists(start_dir):
                found = False
                for d in os.listdir(start_dir):
                    if contract_id in d and os.path.isdir(os.path.join(start_dir, d)):
                        start_dir = os.path.join(start_dir, d)
                        found = True
                        break
                if not found:
                    print(f"Warning: Could not find contract folder matching '{contract_id}' in '{start_dir}'")
                    # We might still want to scan the year or fail? 
                    # For now let's just scan the year folder if contract not found, or return empty?
                    # Let's return empty to be safe if specific contract was requested.
                    return []
            else:
                 return []

    if not os.path.exists(start_dir):
        return []

    results = []
    
    # 2. Walk through the directory
    for root, dirs, files in os.walk(start_dir):
        for name in files:
            # Filter for Excel files (and ignore temporary files starting with ~$)
            if any(name.lower().endswith(ext) for ext in EXCEL_EXTENSIONS) and not name.startswith('~$'):
                folder_name = os.path.basename(root)
                source_type = identify_source_type(name, folder_name)
                if source_type:
                    results.append({
                        'path': os.path.join(root, name),
                        'filename': name,
                        'source_type': source_type,
                        'folder': os.path.basename(root)
                    })
    
    return results
