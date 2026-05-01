# backup.py

import shutil
import os
import datetime
from database import get_current_db_path as get_db_path

def get_backup_folder():
    """Yedeklerin kaydedileceği klasörü oluştur ve döndür"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base_dir, "yedekler")
    if not os.path.exists(backup_dir):
        try:
            os.makedirs(backup_dir)
            print(f"Yedekleme klasörü oluşturuldu: {backup_dir}")
        except Exception as e:
            print(f"Yedekleme klasörü oluşturulamadı: {e}")
            return None
    return backup_dir

def backup_database(backup_name=None):
    """
    Veritabanını yedekler.
    Başarılı olursa yedek dosyasının yolunu, başarısız olursa None döndürür.
    """
    db_path = get_db_path()
    if db_path is None:
        print("Veritabanı yolu alınamadı. (init_db çağrılmamış olabilir)")
        return None

    if not os.path.exists(db_path):
        print(f"Veritabanı dosyası bulunamadı: {db_path}")
        return None
    
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return None
    
    if backup_name is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            db_adi = os.path.splitext(os.path.basename(db_path))[0]
            tr_map = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")
            prefix = db_adi.translate(tr_map).replace(" ", "_")
        except Exception:
            prefix = "pdks"
        backup_name = f"{prefix}_{timestamp}.db"
    
    backup_path = os.path.join(backup_dir, backup_name)
    
    try:
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Yedekleme hatası: {e}")
        return None

def list_backups():
    """Mevcut yedekleri listele (tarihe göre sıralı)"""
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return []
    try:
        files = [f for f in os.listdir(backup_dir) if f.endswith(".db")]
        files.sort(reverse=True)
        return files
    except Exception as e:
        print(f"Yedek listeleme hatası: {e}")
        return []

def restore_database(backup_filename):
    """Belirtilen yedeği geri yükle"""
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return False, "Yedekleme klasörü bulunamadı."
    
    backup_path = os.path.join(backup_dir, backup_filename)
    if not os.path.exists(backup_path):
        return False, "Yedek dosyası bulunamadı."
    
    db_path = get_db_path()
    if db_path is None:
        return False, "Veritabanı yolu alınamadı."
    
    try:
        # Mevcut veritabanını yedekle (güvenlik için)
        temp_backup = backup_database("onceki_hal.db")
        # Yedeği kopyala
        shutil.copy2(backup_path, db_path)
        msg = f"Geri yükleme başarılı."
        if temp_backup:
            msg += f" Önceki hal {os.path.basename(temp_backup)} olarak yedeklendi."
        return True, msg
    except Exception as e:
        return False, str(e)

def clean_old_backups(max_count=30):
    """Eski yedekleri temizle, sadece son max_count kadarını tut"""
    backups = list_backups()
    if len(backups) <= max_count:
        return
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return
    for old in backups[max_count:]:
        try:
            os.remove(os.path.join(backup_dir, old))
            print(f"Eski yedek silindi: {old}")
        except Exception as e:
            print(f"Yedek silme hatası ({old}): {e}")