# database.py

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

_current_db_path = None

def get_db_folder():
    """Veritabanı klasörünü döndürür. Derlenmiş exe için çalışma dizinindeki DATA klasörü, değilse mevcut dizin."""
    if getattr(sys, 'frozen', False):
        # PyInstaller ile derlenmiş exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Normal Python çalışması
        base_path = os.path.dirname(os.path.abspath(__file__))
    db_folder = os.path.join(base_path, "DATA")
    os.makedirs(db_folder, exist_ok=True)
    return db_folder

def set_database(db_name):
    """Veritabanını seçer (dosya adı veya tam yol olabilir)."""
    global _current_db_path
    db_folder = get_db_folder()
    # Eğer db_name tam yol ise onu kullan, değilse DATA klasörü ile birleştir
    if os.path.isabs(db_name):
        _current_db_path = db_name
    else:
        _current_db_path = os.path.join(db_folder, db_name)
    
    # Tabloları kontrol et, yoksa oluştur
    if not os.path.exists(_current_db_path):
        engine = create_engine(f'sqlite:///{_current_db_path}')
        Base.metadata.create_all(engine)
        engine.dispose()
    return _current_db_path

def get_current_db_path():
    return _current_db_path

def get_session():
    if _current_db_path is None:
        raise Exception("Önce set_database ile veritabanı seçilmelidir.")
    engine = create_engine(f'sqlite:///{_current_db_path}')
    Session = sessionmaker(bind=engine)
    return Session()