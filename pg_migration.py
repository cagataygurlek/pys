# pg_migration.py
# SQLite -> PostgreSQL veri taşıma aracı

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from models import Base
from connection_manager import load_config, get_db_folder
import os


def get_sqlite_models():
    """SQLAlchemy model sınıflarını tablo adına göre eşle."""
    return {c.__tablename__: c for c in Base.__subclasses__()}


def table_order():
    """Foreign key bağımlılıklarına göre tablo sırası (önce parent, sonra child)."""
    return [
        "sube", "gorev", "ozel_durum", "izin_turu", "sistem_ayarlari",
        "personel", "puantajlar", "izin", "bordro", "haciz",
        "haciz_odeme", "avans", "kasa_acigi", "sigara_acigi",
        "yillik_izin", "maas_odemeleri", "basvuru_aday", "basvuru_tecrube"
    ]


def get_available_sqlite_dbs():
    """DATA klasöründeki tüm .db dosyalarını listele."""
    folder = get_db_folder()
    if not os.path.exists(folder):
        return []
    return [os.path.join(folder, f) for f in os.listdir(folder)
            if f.endswith(".db") and os.path.isfile(os.path.join(folder, f))]


def migrate_sqlite_to_pg(sqlite_path, pg_host, pg_port, pg_database, pg_user, pg_password, pg_schema):
    """Bir SQLite veritabanını PostgreSQL schema'sına taşır."""
    sqlite_url = f"sqlite:///{sqlite_path}"
    pg_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

    sqlite_engine = create_engine(sqlite_url)
    pg_engine = create_engine(pg_url)

    with pg_engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS \"{pg_schema}\""))
        conn.execute(text(f"SET search_path TO \"{pg_schema}\""))
        conn.commit()

    Base.metadata.create_all(pg_engine)

    pg_engine_dispo = create_engine(pg_url)
    with pg_engine_dispo.connect() as conn:
        conn.execute(text(f"SET search_path TO \"{pg_schema}\""))
        conn.commit()
    PgSession = sessionmaker(bind=pg_engine_dispo)

    sqlite_conn = sqlite_engine.connect()
    models_map = get_sqlite_models()

    tables = table_order()
    total_rows = 0

    for table_name in tables:
        model_class = models_map.get(table_name)
        if not model_class:
            print(f"[{table_name}] Model bulunamadı, atlanıyor.")
            continue

        columns = [c.name for c in model_class.__table__.columns]
        col_list = ", ".join(columns)
        placeholders = ", ".join([f":{c}" for c in columns])

        try:
            rows = sqlite_conn.execute(text(f"SELECT {col_list} FROM \"{table_name}\"")).mappings().all()
        except Exception as e:
            print(f"[{table_name}] SQLite okuma hatası: {e}")
            continue

        if not rows:
            print(f"[{table_name}] 0 satır (boş).")
            continue

        pg_session = PgSession()
        try:
            for row in rows:
                row_dict = dict(row)
                pg_session.execute(
                    text(f"INSERT INTO \"{pg_schema}\".\"{table_name}\" ({col_list}) VALUES ({placeholders})"),
                    row_dict
                )
            pg_session.commit()
            print(f"[{table_name}] {len(rows)} satır taşındı.")
            total_rows += len(rows)
        except Exception as e:
            pg_session.rollback()
            print(f"[{table_name}] HATA: {e}")
        finally:
            pg_session.close()

    sqlite_conn.close()
    sqlite_engine.dispose()
    pg_engine_dispo.dispose()
    pg_engine.dispose()

    return total_rows


if __name__ == "__main__":
    print("=== SQLite → PostgreSQL Veri Taşıma Aracı ===\n")

    config = load_config()
    pg = config.get("postgresql", {})

    host = input(f"PG Host [{pg.get('host', 'localhost')}]: ") or pg.get("host", "localhost")
    port = input(f"PG Port [{pg.get('port', 5432)}]: ") or str(pg.get("port", 5432))
    database = input(f"PG Database [{pg.get('database', 'pys')}]: ") or pg.get("database", "pys")
    user = input(f"PG User [{pg.get('user', 'postgres')}]: ") or pg.get("user", "postgres")
    password = input("PG Password: ") or pg.get("password", "")

    dbs = get_available_sqlite_dbs()
    if not dbs:
        print("DATA klasöründe hiç .db dosyası bulunamadı!")
        exit(1)

    print("\nSQLite veritabanları:")
    for i, db in enumerate(dbs):
        firma = os.path.splitext(os.path.basename(db))[0]
        size = os.path.getsize(db) // 1024
        print(f"  [{i}] {firma} ({size} KB)")

    secim = input(f"\nTaşınacak DB index (0-{len(dbs)-1}): ")
    try:
        idx = int(secim)
        sqlite_path = dbs[idx]
    except (ValueError, IndexError):
        print("Geçersiz seçim!")
        exit(1)

    firma_adi = os.path.splitext(os.path.basename(sqlite_path))[0]
    schema = input(f"Hedef schema [{firma_adi}]: ") or firma_adi

    print(f"\nTaşıma başlıyor: {os.path.basename(sqlite_path)} → {host}/{database}/{schema}")
    total = migrate_sqlite_to_pg(sqlite_path, host, int(port), database, user, password, schema)
    print(f"\n✅ Taşıma tamamlandı! Toplam {total} satır aktarıldı.")
