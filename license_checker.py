# license_checker.py
import json
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = 'service_account.json'  # indirdiğiniz dosya
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def check_license(license_key):
    """Girilen anahtarı Drive'daki license_data.json içinde arar."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    
    # Lisans dosyasının Drive ID'si (sabit)
    file_id = '1A2B3C4D5E...'  # kendi dosyanızın ID'si
    
    # Dosyayı indir
    request = service.files().get_media(fileId=file_id)
    content = request.execute()
    data = json.loads(content.decode('utf-8'))
    
    # Lisans araştırması
    for lic in data.get('licenses', []):
        if lic['key'] == license_key:
            if lic['status'] == 'active':
                return True, lic.get('expire_date')
            else:
                return False, "Lisans pasif veya süresi dolmuş."
    return False, "Geçersiz lisans anahtarı."