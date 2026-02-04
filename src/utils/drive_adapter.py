import os
import io
import pickle
import pandas as pd
from typing import List, Dict, Optional, Union
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

# Scopes required
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

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
                fileId=file_id, fields='id, name, mimeType').execute()
        except Exception as e:
            print(f"Get Metadata Error: {e}")
            return {}

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
            print(f"Drive Read Error ({file_id}): {e}")
            return None
