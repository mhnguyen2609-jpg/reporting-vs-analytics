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
            
    # Apply Overrides based on Folder/Prefix context
    if match:
        # If match is VT_NHAP (DMVTN) but folder is XUAT or prefix is TC -> Override to VT_XUAT
        if match == 'VT_NHAP':
             if folder_upper == 'XUAT' or filename_upper.startswith('TC'):
                 return 'VT_XUAT'
    
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

def scan_drive_files(drive_client: GoogleDriveClient, folder_id: str) -> List[Dict]:
    """
    Scans for Excel files in the specified Google Drive folder.
    
    Args:
        drive_client: Instance of GoogleDriveClient.
        folder_id: The Drive folder ID to scan (Contract folder ID).
        
    Returns:
        List of dictionaries containing file metadata:
        {
            'file_id': Drive File ID,
            'filename': filename,
            'source_type': identified type or None
        }
    """
    results = []
    # Use list_excel_files from adapter
    files = drive_client.list_excel_files(folder_id)
    
    for f in files:
        name = f['name']
        file_id = f['id']
        # We don't strictly have 'folder_name' here unless we get parent info, 
        # but identify_source_type mostly relies on filename. 
        # If folder context is critical, we might need to pass it in.
        # For now assuming filename is enough or we rely on the implementation.
        source_type = identify_source_type(name)
        
        if source_type:
            results.append({
                'file_id': file_id,
                'filename': name,
                'source_type': source_type,
                # 'folder': ... # We can pass the contract/parent folder name if needed?
            })
            
    return results
