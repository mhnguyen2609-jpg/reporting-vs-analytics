import os
import io
import pickle
import pandas as pd
from typing import List, Dict, Optional, Union
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

# Scopes required (need write access for cache persistence)
SCOPES = ['https://www.googleapis.com/auth/drive']

class GoogleDriveClient:
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        """
        Initializes the Google Drive client.
        Prioritizes Service Account (credentials.json) if available.
        Otherwise falls back to OAuth user flow (token.pickle).
        """
        self.creds = None
        self.service = None
        
        # 1. Try Service Account first (Preferred for server/streamlit)
        # Check Streamlit secrets first (for Cloud Deployment)
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and st.secrets and "gcp_service_account" in st.secrets:
                self.creds = Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"], scopes=SCOPES)
                self.service = build('drive', 'v3', credentials=self.creds)
                print("[OK] Drive Client: Loaded from Streamlit secrets")
                return
        except Exception:
            pass # Secrets not available, continue to file-based auth

        if os.path.exists(credentials_path):
            try:
                self.creds = Credentials.from_service_account_file(
                    credentials_path, scopes=SCOPES)
                print(f"[OK] Drive Client: Loaded from {credentials_path}")
            except Exception as e:
                print(f"[ERROR] Error loading service account: {e}")

        # 2. If no service account, try User Auth (OAuth)
        if not self.creds:
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in.
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    # Only run this locally; on Streamlit Cloud this won't work without secrets
                    if os.path.exists('client_secret.json'):
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'client_secret.json', SCOPES)
                        self.creds = flow.run_local_server(port=0)
                        # Save the credentials for the next run
                        with open(token_path, 'wb') as token:
                            pickle.dump(self.creds, token)
        
        if self.creds:
            self.service = build('drive', 'v3', credentials=self.creds)
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)
            print("[OK] Drive Client: Service initialized successfully")
        else:
            print("[ERROR] Warning: No valid credentials found. Drive features will not work.")

    def list_folders(self, parent_id: str) -> List[Dict]:
        """
        Lists subfolders within a given parent folder.
        Returns: List of dicts {'id': '...', 'name': '...'}
        """
        if not self.service: return []
        
        results = []
        page_token = None
        
        query = f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        
        try:
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name)',
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            return results
        except Exception as e:
            print(f"Drive List Folders Error: {e}")
            return []

    def list_excel_files(self, parent_id: str) -> List[Dict]:
        """
        Recursively finds all Excel files in the folder structure is too slow.
        Better to list files in a specific folder. 
        For deep scanning, we might need a more optimized approach or just scan direct children if structure is flat.
        
        For now, let's assume we list files in a specific folder (like a Contract folder).
        """
        if not self.service: return []
        
        results = []
        page_token = None
        
        # Query for Excel files
        # MIME types for Excel: 
        # application/vnd.openxmlformats-officedocument.spreadsheetml.sheet (.xlsx)
        # application/vnd.ms-excel (.xls)
        query = f"'{parent_id}' in parents and (mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType = 'application/vnd.ms-excel') and trashed = false"
        
        try:
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType)',
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            return results
        except Exception as e:
            print(f"Drive List Files Error: {e}")
            return []
            

            
    def get_file_metadata(self, file_id: str) -> Dict:
        """Get metadata (name, mimeType) for a file/folder."""
        if not self.service: return {}
        try:
            return self.service.files().get(
                fileId=file_id, fields='id, name, mimeType, modifiedTime').execute()
        except Exception as e:
            print(f"Get Metadata Error: {e}")
            return {}

    def get_folder_modified_times(self, folder_ids: list) -> Dict[str, str]:
        """
        Get modifiedTime for multiple folders in a single batch.
        Returns dict: {folder_id: modifiedTime}
        """
        if not self.service or not folder_ids:
            return {}
        
        result = {}
        try:
            # Use batch request for efficiency
            batch = self.service.new_batch_http_request()
            
            def callback(request_id, response, exception):
                if exception:
                    print(f"Batch Error for {request_id}: {exception}")
                else:
                    result[request_id] = response.get('modifiedTime', '')
            
            for fid in folder_ids:
                batch.add(
                    self.service.files().get(fileId=fid, fields='id, modifiedTime'),
                    request_id=fid,
                    callback=callback
                )
            
            batch.execute()
        except Exception as e:
            print(f"Batch Request Error: {e}")
        
        return result

    def read_excel(self, file_id: str) -> Optional[bytes]:
        """
        Downloads file content as bytes.
        """
        if not self.service: return None
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return fh.getvalue()
        except Exception as e:

    # ============================================================
    # GOOGLE SHEETS METHODS (CACHE DB)
    # ============================================================
    
    def create_sheet(self, folder_id: str, title: str) -> Optional[str]:
        """Create a new Google Sheet in the specified folder. Returns Spreadsheet ID."""
        if not self.sheets_service: return None
        try:
            # 1. Create Spreadsheet
            spreadsheet = {'properties': {'title': title}}
            spreadsheet = self.sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            
            # 2. Key Step: Move it to the correct folder
            # New files are created in root. Need to add parent folder and remove from root.
            file = self.service.files().get(fileId=spreadsheet_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            self.service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            print(f"[OK] Created Sheet '{title}' in folder '{folder_id}'")
            return spreadsheet_id
        except Exception as e:
            print(f"Create Sheet Error: {e}")
            return None

    def write_sheet_data(self, spreadsheet_id: str, range_name: str, values: List[List]):
        """Write 2D list to specific range."""
        if not self.sheets_service: return False
        try:
            body = {'values': values}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=range_name,
                valueInputOption='RAW', body=body
            ).execute()
            return True
        except Exception as e:
            print(f"Write Sheet Error: {e}")
            return False

    def read_sheet_data(self, spreadsheet_id: str, range_name: str) -> List[List]:
        """Read 2D list from specific range."""
        if not self.sheets_service: return []
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            return result.get('values', [])
        except Exception as e:
            print(f"Read Sheet Error: {e}")
            return []
    
    def clear_sheet_range(self, spreadsheet_id: str, range_name: str):
        """Clear values in range."""
        if not self.sheets_service: return False
        try:
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            return True
        except Exception as e:
            print(f"Clear Sheet Error: {e}")
            return False

    # ============================================================
    # CACHE PERSISTENCE METHODS
    # ============================================================
    
    def find_file_in_folder(self, folder_id: str, filename: str) -> Optional[str]:
        """Find a file by name in a specific folder. Returns file_id or None."""
        if not self.service: return None
        try:
            query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
            response = self.service.files().list(
                q=query, fields='files(id, name)', pageSize=1).execute()
            files = response.get('files', [])
            return files[0]['id'] if files else None
        except Exception as e:
            print(f"Find File Error: {e}")
            return None
    
    def download_text_file(self, file_id: str) -> Optional[str]:
        """Download a text file and return its content as string."""
        content = self.read_excel(file_id)  # Same method works for any file
        if content:
            return content.decode('utf-8')
        return None
    
    def upload_file(self, folder_id: str, filename: str, content: str, 
                    mime_type: str = 'application/json') -> Optional[str]:
        """
        Upload or update a file in the specified folder.
        Returns file_id on success, None on failure.
        """
        if not self.service: return None
        
        try:
            # Check if file already exists
            existing_id = self.find_file_in_folder(folder_id, filename)
            
            # Prepare content
            file_content = io.BytesIO(content.encode('utf-8'))
            media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
            
            if existing_id:
                # Update existing file
                file = self.service.files().update(
                    fileId=existing_id,
                    media_body=media
                ).execute()
                print(f"[OK] Cache updated: {filename}")
                return file.get('id')
            else:
                # Create new file
                file_metadata = {
                    'name': filename,
                    'parents': [folder_id],
                    'mimeType': mime_type
                }
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"[OK] Cache created: {filename}")
                return file.get('id')
        except Exception as e:
            print(f"Upload File Error: {e}")
            return None
