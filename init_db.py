# init_db.py
from database import engine, SessionLocal
from models import Base, IzinTuru, Sube, Gorev, OzelDurum

def init_database():
    print("Veritabanı oluşturuluyor...")
    
    # Tüm tabloları oluştur
    Base.metadata.create_all(bind=engine)
    print("Tablolar oluşturuldu.")
    
    # Session oluştur
    session = SessionLocal()
    
    # Varsayılan izin türlerini ekle
    izin_turleri = [
        {"ad": "Yıllık İzin", "renk": "#3498db", "ucretli_mi": True},
        {"ad": "Hastalık İzni", "renk": "#e74c3c", "ucretli_mi": True},
        {"ad": "Mazeret İzni", "renk": "#f39c12", "ucretli_mi": True},
        {"ad": "Ücretsiz İzin", "renk": "#95a5a6", "ucretli_mi": False},
        {"ad": "Doğum İzni", "renk": "#9b59b6", "ucretli_mi": True},
        {"ad": "Evlilik İzni", "renk": "#e67e22", "ucretli_mi": True},
        {"ad": "Ölüm İzni", "renk": "#2c3e50", "ucretli_mi": True},
    ]
    
    for izin in izin_turleri:
        var_mi = session.query(IzinTuru).filter(IzinTuru.ad == izin["ad"]).first()
        if not var_mi:
            yeni_izin = IzinTuru(**izin)
            session.add(yeni_izin)
            print(f"  + {izin['ad']} eklendi.")
    
    # Varsayılan şube ekle (eğer yoksa)
    if session.query(Sube).count() == 0:
        varsayilan_sube = Sube(ad="Merkez Şube")
        session.add(varsayilan_sube)
        print("  + Merkez Şube eklendi.")
    
    # Varsayılan görev ekle
    if session.query(Gorev).count() == 0:
        varsayilan_gorev = Gorev(ad="Personel")
        session.add(varsayilan_gorev)
        print("  + Personel görevi eklendi.")
    
    session.commit()
    print("Varsayılan veriler eklendi.")
    session.close()
    print("Veritabanı başarıyla oluşturuldu!")

if __name__ == "__main__":
    init_database()