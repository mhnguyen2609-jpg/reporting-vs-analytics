import os
from typing import List, Dict, Optional
from src.core.constants import DEFAULT_ROOT_PATH, NamingKeywords, EXCEL_EXTENSIONS
from src.utils.drive_adapter import GoogleDriveClient

def identify_source_type(filename: str, folder_name: str = None) -> Optional[str]:
    """
    Identifies the source type based on the filename using keywords defined in constants.py.
    Prioritizes longer keywords/more specific matches.
    Also considers folder name for context-aware identification.
    """
    filename_upper = filename.upper()
    folder_upper = folder_name.upper() if folder_name else ""
    
    # Sort keywords by length in descending order to match longest first (e.g. DMVTN-VAN before DMVTN)
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
            
    # Fallback: Check Folder Name if Filename has no match
    if not match and folder_upper:
        for type_name, keyword in all_keywords:
            # Strict check for folder? Or contains?
            # "DMVTN" folder containing "data.xlsx" -> match VT_NHAP.
            if keyword in folder_upper:
                match = type_name
                break

    # Apply Overrides based on Folder/Prefix context
    if match:
        # If match is VT_NHAP (DMVTN) but folder is XUAT or prefix is TC -> Override to VT_XUAT
        if match == 'VT_NHAP':
             if folder_upper == 'XUAT' or filename_upper.startswith('TC'):
                 match = 'VT_XUAT'
    
    return match

def scan_project_files(target_dir: str = DEFAULT_ROOT_PATH) -> List[Dict]:
    """
    Scans a local directory for Excel files and identifies their source type.
    """
    results = []
    if not os.path.exists(target_dir):
        return []
        
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            if not any(filename.lower().endswith(ext) for ext in EXCEL_EXTENSIONS):
                continue
                
            # Skip temp files
            if filename.startswith('~$'):
                continue
                
            full_path = os.path.join(root, filename)
            # Identify type
            # Pass folder name for context if needed (e.g. parent folder)
            folder_name = os.path.basename(root)
            source_type = identify_source_type(filename, folder_name)
            
            if source_type:
                results.append({
                    'path': full_path,
                    'filename': filename,
                    'source_type': source_type,
                    'last_modified': os.path.getmtime(full_path)
                })
    return results

def scan_drive_files(drive_client: GoogleDriveClient, folder_id: str, folder_name: str = None,
                     current_depth: int = 0, max_depth: int = 5, visited: set = None) -> List[Dict]:
    """
    Recursively scans for Excel files in the specified Google Drive folder and its subfolders.
    Limits recursion depth to prevent infinite loops.
    """
    if visited is None: visited = set()
    if folder_id in visited: return []
    visited.add(folder_id)
    
    if current_depth > max_depth:
        print(f"⚠️ Max depth {max_depth} reached at folder {folder_name or folder_id}")
        return []

    results = []
    
    # 1. Get all Excel files directly in this folder
    files = drive_client.list_excel_files(folder_id)
    
    for f in files:
        name = f['name']
        file_id = f['id']
        source_type = identify_source_type(name, folder_name)
        
        # Include all Excel files, even if type is unknown
        results.append({
            'file_id': file_id,
            'filename': name,
            'source_type': source_type,
        })
    
    # 2. Recursively scan subfolders
    subfolders = drive_client.list_folders(folder_id)
    for subfolder in subfolders:
        sub_results = scan_drive_files(
            drive_client, 
            subfolder['id'], 
            subfolder['name'],
            current_depth=current_depth + 1,
            max_depth=max_depth,
            visited=visited
        )
        results.extend(sub_results)
            
    return results
