# guncelle.py
import os
import glob
from database import set_database, get_session
from sqlalchemy import text

# 1) data klasöründeki tüm .db dosyalarını bul
ana_dizin = os.path.dirname(os.path.abspath(__file__))
data_klasoru = os.path.join(ana_dizin, "data")
db_dosyalari = glob.glob(os.path.join(data_klasoru, "*.db"))

if not db_dosyalari:
    print("❌ 'data' klasöründe hiç .db dosyası bulunamadı.")
    exit(1)

print(f"Toplam {len(db_dosyalari)} veritabanı bulundu.\n")

for db_yolu in db_dosyalari:
    print(f"İşleniyor: {db_yolu}")
    try:
        # Veritabanını seç
        set_database(db_yolu)
        session = get_session()
        engine = session.get_bind()

        with engine.connect() as conn:
            # Mevcut sütunları kontrol et
            result = conn.execute(text("PRAGMA table_info(bordro)"))
            sutunlar = [row[1] for row in result.fetchall()]

            if 'bekleyen_haciz_tutari' not in sutunlar:
                conn.execute(text(
                    "ALTER TABLE bordro ADD COLUMN bekleyen_haciz_tutari FLOAT DEFAULT 0.0"
                ))
                conn.commit()
                print("   ✅ 'bekleyen_haciz_tutari' sütunu eklendi.")
            else:
                print("   ℹ️ Sütun zaten mevcut.")
        session.close()
    except Exception as e:
        print(f"   ❌ Hata: {e}")

print("\n🎉 Tüm veritabanları güncellendi.")