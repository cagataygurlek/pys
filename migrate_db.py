import sqlite3
import os
from database import get_session  # eğer database.py varsa

def add_columns():
    # Önce database.py'deki veritabanı yolunu bulmaya çalış
    try:
        from database import get_engine
        engine = get_engine()
        db_url = str(engine.url)
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
        else:
            # Varsayılan yol
            db_path = os.path.join(os.path.dirname(__file__), "fresh.db")
    except:
        db_path = os.path.join(os.path.dirname(__file__), "fresh.db")

    # Mevcut dosyayı kontrol et
    if not os.path.exists(db_path):
        print(f"Veritabanı dosyası bulunamadı: {db_path}")
        # Proje dizinindeki tüm .db dosyalarını listele
        db_files = [f for f in os.listdir('.') if f.endswith('.db')]
        if db_files:
            print(f"Mevcut .db dosyaları: {db_files}")
            db_path = db_files[0]  # ilkini al
            print(f"Seçilen: {db_path}")
        else:
            print("Hiç .db dosyası bulunamadı. Uygulamayı ilk kez çalıştırıyorsanız önce uygulamayı bir kez çalıştırın.")
            return

    print(f"Veritabanı dosyası: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Mevcut sütunları kontrol et
    cursor.execute("PRAGMA table_info(personel)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'baba_adi' not in columns:
        cursor.execute("ALTER TABLE personel ADD COLUMN baba_adi VARCHAR(100)")
        print("baba_adi sütunu eklendi.")
    if 'dogum_yeri' not in columns:
        cursor.execute("ALTER TABLE personel ADD COLUMN dogum_yeri VARCHAR(100)")
        print("dogum_yeri sütunu eklendi.")
    if 'dogum_tarihi' not in columns:
        cursor.execute("ALTER TABLE personel ADD COLUMN dogum_tarihi DATE")
        print("dogum_tarihi sütunu eklendi.")

    conn.commit()
    conn.close()
    print("Veritabanı güncellendi.")

if __name__ == "__main__":
    add_columns()