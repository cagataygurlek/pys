# migrate_to_pg.py
# SQLite'deki verileri PostgreSQL'e (Neon) aktarır (batch mode)

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import IntegrityError
from models import Base

SQLITE_PATH = "DATA/Beşler.db"
PG_URL = "postgresql://neondb_owner:npg_STdJCPu2Ll3U@ep-sweet-truth-at28khnr.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

TABLO_SIRASI = [
    "sube", "gorev", "ozel_durum", "izin_turu", "kullanici", "sistem_ayarlari",
    "personel", "basvuru_aday", "kullanici_sube", "kullanici_yetki",
    "izin", "yillik_izin", "haciz", "bordro", "puantajlar",
    "maas_odemeleri", "avans", "kasa_acigi", "sigara_acigi",
    "haciz_odeme", "basvuru_tecrube",
]

print("SQLite bağlanıyor...")
sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")

print("PostgreSQL (Neon) bağlanıyor...")
pg_engine = create_engine(PG_URL, pool_size=1)

print("PostgreSQL boolean kolonlar tespit ediliyor...")
pg_inspector = inspect(pg_engine)
boolean_cols = {}
for tablo in TABLO_SIRASI:
    cols = pg_inspector.get_columns(tablo)
    bools = [c["name"] for c in cols if str(c.get("type", "")) == "BOOLEAN"]
    if bools:
        boolean_cols[tablo] = bools

print("PostgreSQL tabloları oluşturuluyor...")
Base.metadata.create_all(pg_engine)

print("Veriler aktarılıyor...")
with sqlite_engine.connect() as sqlite_conn, pg_engine.connect() as pg_conn:
    for tablo in TABLO_SIRASI:
        rows = sqlite_conn.execute(text(f"SELECT * FROM \"{tablo}\"")).fetchall()
        if not rows:
            print(f"  {tablo}: 0 satır")
            continue

        col_names = rows[0]._fields
        all_data = []
        for row in rows:
            data = dict(zip(col_names, row))
            if tablo in boolean_cols:
                for bc in boolean_cols[tablo]:
                    if bc in data and data[bc] is not None:
                        data[bc] = bool(data[bc])
            all_data.append(data)

        placeholders = ", ".join(f":{c}" for c in col_names)
        cols = ", ".join(f"\"{c}\"" for c in col_names)
        sql = text(f"INSERT INTO \"{tablo}\" ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")

        # Her 20 satırda bir batch ekle (FK hatalarını tek tek atla)
        ok = 0
        hatali = 0
        for i in range(0, len(all_data), 20):
            batch = all_data[i:i+20]
            try:
                pg_conn.execute(sql, batch)
                ok += len(batch)
            except IntegrityError:
                pg_conn.rollback()
                for data in batch:
                    pg_conn.execute(text("SAVEPOINT sp"))
                    try:
                        pg_conn.execute(sql, data)
                        pg_conn.execute(text("RELEASE SAVEPOINT sp"))
                        ok += 1
                    except IntegrityError:
                        pg_conn.execute(text("ROLLBACK TO SAVEPOINT sp"))
                        hatali += 1
            pg_conn.commit()

        print(f"  {tablo}: {ok} satır", end="")
        if hatali:
            print(f", {hatali} atlandı")
        else:
            print()

    print("Sequence'lar güncelleniyor...")
    for tablo in TABLO_SIRASI:
        cols = pg_inspector.get_columns(tablo)
        pk_cols = [c["name"] for c in cols if c.get("primary_key", False)]
        if pk_cols:
            pk = pk_cols[0]
            result = pg_conn.execute(text(f"SELECT COALESCE(MAX(\"{pk}\"), 0) FROM \"{tablo}\""))
            max_id = result.scalar()
            seq_name = f"\"{tablo}_{pk}_seq\""
            try:
                pg_conn.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH {max_id + 1}"))
            except Exception:
                pass
    pg_conn.commit()

sqlite_engine.dispose()
pg_engine.dispose()
print("\nMigration tamamlandı!")
