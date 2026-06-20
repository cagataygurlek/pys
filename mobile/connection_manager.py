# connection_manager.py

import os
import json
import sys
import hashlib
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from models import Base, Kullanici

CONFIG_FILENAME = "pys_connection.json"

_engine = None
_SessionLocal = None
_current_db_type = "sqlite"
_current_firma = None
_current_db_path = None
_current_pg_schema = None


def _get_config_dir():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return base


def _get_config_path():
    return os.path.join(_get_config_dir(), CONFIG_FILENAME)


def _get_default_config():
    return {
        "type": "sqlite",
        "sqlite": {
            "current_db": None
        },
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "database": "pys",
            "user": "pys_user",
            "password": "",
            "current_schema": None
        }
    }


def load_config():
    config_path = _get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return _get_default_config()


def save_config(config):
    config_path = _get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Config kaydedilemedi: {e}")


def get_db_folder():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    db_folder = os.path.join(base_path, "DATA")
    os.makedirs(db_folder, exist_ok=True)
    return db_folder


def _dispose_engine():
    global _engine, _SessionLocal
    if _engine:
        try:
            _engine.dispose()
        except Exception:
            pass
        _engine = None
        _SessionLocal = None


def _varsayilan_admin_olustur(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        mevcut = session.query(Kullanici).filter(Kullanici.username == "admin").first()
        if not mevcut:
            sifre_hash = hashlib.sha256("admin123".encode()).hexdigest()
            admin = Kullanici(
                username="admin",
                password_hash=sifre_hash,
                ad_soyad="Admin Kullanıcı",
                admin=True,
                aktif=True
            )
            session.add(admin)
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def init_sqlite(db_name_or_path):
    global _engine, _SessionLocal, _current_db_type, _current_firma, _current_db_path, _current_pg_schema
    _dispose_engine()

    db_folder = get_db_folder()
    if os.path.isabs(db_name_or_path):
        db_path = db_name_or_path
    else:
        db_path = os.path.join(db_folder, db_name_or_path)

    if not os.path.exists(db_path):
        engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(engine)
        _varsayilan_admin_olustur(engine)
        engine.dispose()

    _current_db_type = "sqlite"
    _current_db_path = db_path
    _current_firma = os.path.splitext(os.path.basename(db_path))[0]
    _current_pg_schema = None
    _engine = create_engine(
        f'sqlite:///{db_path}',
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
    _SessionLocal = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)
    _varsayilan_admin_olustur(_engine)

    config = load_config()
    config["type"] = "sqlite"
    config["sqlite"]["current_db"] = os.path.basename(db_path)
    save_config(config)

    return db_path


def _pg_set_search_path(dbapi_connection, connection_record):
    """Event listener: her bağlantıda search_path'i ayarla."""
    cursor = dbapi_connection.cursor()
    cursor.execute(f'SET search_path TO "{_current_pg_schema}"')
    cursor.close()


def init_postgresql(host, port, database, user, password, schema):
    global _engine, _SessionLocal, _current_db_type, _current_firma, _current_db_path, _current_pg_schema
    _dispose_engine()

    url = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
    _current_db_type = "postgresql"
    _current_db_path = url
    _current_firma = schema
    _current_pg_schema = schema

    _engine = create_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": 15},
        pool_timeout=60
    )

    event.listen(_engine, "connect", _pg_set_search_path)

    with _engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS \"{schema}\""))
        conn.commit()

    Base.metadata.create_all(_engine)
    _varsayilan_admin_olustur(_engine)
    _SessionLocal = sessionmaker(bind=_engine)

    config = load_config()
    config["type"] = "postgresql"
    config["postgresql"]["host"] = host
    config["postgresql"]["port"] = port
    config["postgresql"]["database"] = database
    config["postgresql"]["user"] = user
    config["postgresql"]["password"] = password
    config["postgresql"]["current_schema"] = schema
    save_config(config)


def set_database(db_name):
    if db_name and db_name.startswith("postgresql://"):
        from urllib.parse import urlparse, parse_qs
        qs_part = db_name.split("?", 1)[1] if "?" in db_name else ""
        qs_params = parse_qs(qs_part)
        clean = db_name.replace("postgresql://", "postgresql+psycopg2://", 1).split("?")[0]
        parsed = urlparse(clean)
        host = parsed.hostname
        port = parsed.port or 5432
        user = parsed.username
        password = parsed.password or ""
        path = parsed.path.lstrip("/")
        parts = path.split("/")
        database = parts[0] if parts else "neondb"
        schema = qs_params.get("schema", ["public"])[0]
        init_postgresql(host, port, database, user, password, schema)
    else:
        init_sqlite(db_name)
    return _current_db_path


def get_session():
    if _SessionLocal is None:
        raise Exception("Veritabanı bağlantısı henüz kurulmadı.")
    return _SessionLocal()


def get_current_db_path():
    return _current_db_path


def get_current_firma():
    return _current_firma


def get_db_type():
    return _current_db_type


def keepalive():
    """Neon cold start engellemek için periyodik ping (her 60 sn)."""
    global _engine
    if _engine and _current_db_type == "postgresql":
        try:
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            pass


def get_pg_schema():
    return _current_pg_schema


def test_postgresql_connection(host, port, database, user, password):
    try:
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        test_engine = create_engine(url, pool_pre_ping=True)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        return True, "Bağlantı başarılı!"
    except Exception as e:
        return False, str(e)


def create_pg_database(host, port, user, password, new_db_name):
    """PostgreSQL üzerinde yeni bir boş veritabanı oluşturur."""
    try:
        url = f"postgresql://{user}:{password}@{host}:{port}/postgres"
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text(f'CREATE DATABASE "{new_db_name}"'))
        engine.dispose()
        return True, f"✅ '{new_db_name}' veritabanı oluşturuldu!"
    except Exception as e:
        err = str(e)
        if 'already exists' in err:
            return False, f"⚠️ '{new_db_name}' veritabanı zaten mevcut."
        return False, f"❌ Oluşturma hatası: {err}"


def list_pg_schemas(host, port, database, user, password):
    try:
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        test_engine = create_engine(url)
        with test_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'public', 'pg_toast') "
                "ORDER BY schema_name"
            ))
            schemas = [row[0] for row in result]
        test_engine.dispose()
        return schemas
    except Exception as e:
        print(f"Schema listeleme hatası: {e}")
        return []
