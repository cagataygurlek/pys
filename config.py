# config.py

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Veritabanı klasörü
DB_FOLDER = os.path.join(BASE_DIR, "veritabanlari")

# Firma listesi (klasör adları)
FIRMALAR = ["firma1", "firma2"]  # İstediğiniz kadar ekleyin

def get_db_path(firma_adi):
    """Firma adına göre veritabanı yolunu döndürür"""
    return os.path.join(DB_FOLDER, firma_adi, f"{firma_adi}.db")