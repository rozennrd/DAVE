import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload




def upload_to_cloud(filename):
    
    # === CONFIGURATION ===
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(CURRENT_DIR) 
    CREDENTIALS_PATH = os.path.join(CURRENT_DIR, "utils", "credentials.json")
    TOKEN_PATH = os.path.join(CURRENT_DIR, "token.json")
    SCOPES = ['https://www.googleapis.com/auth/drive']
    FOLDER_ID = '1JEbyPwCxxMo9eDi8gM3Pxn-vOekLFiBU'  # Dossier cible
    FILE_TO_UPLOAD_PATH = os.path.join(PARENT_DIR, filename)
    
    # === ÉTAPE 1 : Création d'un DataFrame pandas ===
    df = pd.read_csv(FILE_TO_UPLOAD_PATH)


    # === ÉTAPE 2 : Authentification Google ===
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)

    # === ÉTAPE 3 : Upload du fichier CSV dans le dossier Drive ===
    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(filename, mimetype='text/csv')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    print(f"CSV uploadé avec succès dans le dossier ! ID: {file.get('id')}")
