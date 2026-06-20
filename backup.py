# backup.py

import shutil
import os
import datetime
import subprocess
from database import get_current_db_path as get_db_path, get_db_type


def get_backup_folder():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base_dir, "yedekler")
    if not os.path.exists(backup_dir):
        try:
            os.makedirs(backup_dir)
        except Exception as e:
            print(f"Yedekleme klasörü oluşturulamadı: {e}")
            return None
    return backup_dir


def backup_database(backup_name=None):
    db_path = get_db_path()
    if db_path is None:
        print("Veritabanı yolu alınamadı.")
        return None

    db_type = get_db_type()
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return None

    if backup_name is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            firma = os.path.splitext(os.path.basename(str(db_path)))[0] if db_type == "sqlite" else "pg"
            tr_map = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")
            prefix = firma.translate(tr_map).replace(" ", "_")
        except Exception:
            prefix = "pdks"
        backup_name = f"{prefix}_{timestamp}.db"

    backup_path = os.path.join(backup_dir, backup_name)

    if db_type == "pg" or db_type == "postgresql":
        return _pg_backup(backup_path)
    else:
        return _sqlite_backup(backup_path)


def _sqlite_backup(backup_path):
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Veritabanı dosyası bulunamadı: {db_path}")
        return None
    try:
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"SQLite yedekleme hatası: {e}")
        return None


def _pg_backup(backup_path):
    from connection_manager import load_config
    config = load_config()
    pg = config.get("postgresql", {})
    host = pg.get("host", "localhost")
    port = str(pg.get("port", 5432))
    database = pg.get("database", "pys")
    user = pg.get("user", "postgres")
    schema = pg.get("current_schema", "public")

    output_path = backup_path.replace(".db", ".sql")
    try:
        subprocess.run(
            ["pg_dump", "-h", host, "-p", port, "-U", user, "-n", schema,
             "-f", output_path, database],
            check=True, capture_output=True, text=True,
            env={**os.environ, "PGPASSWORD": pg.get("password", "")}
        )
        return output_path
    except FileNotFoundError:
        print("pg_dump bulunamadı. PG-Backup için PostgreSQL kurulumunda pg_dump gereklidir.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"PostgreSQL yedekleme hatası ({e.returncode}): {e.stderr}")
        return None


def list_backups():
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return []
    try:
        files = [f for f in os.listdir(backup_dir)
                 if f.endswith(".db") or f.endswith(".sql")]
        files.sort(reverse=True)
        return files
    except Exception as e:
        print(f"Yedek listeleme hatası: {e}")
        return []


def restore_database(backup_filename):
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return False, "Yedekleme klasörü bulunamadı."

    backup_path = os.path.join(backup_dir, backup_filename)
    if not os.path.exists(backup_path):
        return False, "Yedek dosyası bulunamadı."

    db_path = get_db_path()
    if db_path is None:
        return False, "Veritabanı yolu alınamadı."

    db_type = get_db_type()
    if db_type == "postgresql" or db_type == "pg":
        return _pg_restore(backup_path)
    else:
        return _sqlite_restore(backup_path)


def _sqlite_restore(backup_path):
    db_path = get_db_path()
    try:
        temp_backup = backup_database("onceki_hal.db")
        shutil.copy2(backup_path, db_path)
        msg = "Geri yükleme başarılı."
        if temp_backup:
            msg += f" Önceki hal {os.path.basename(temp_backup)} olarak yedeklendi."
        return True, msg
    except Exception as e:
        return False, str(e)


def _pg_restore(backup_path):
    from connection_manager import load_config
    config = load_config()
    pg = config.get("postgresql", {})
    host = pg.get("host", "localhost")
    port = str(pg.get("port", 5432))
    database = pg.get("database", "pys")
    user = pg.get("user", "postgres")
    schema = pg.get("current_schema", "public")

    if backup_path.endswith(".sql"):
        try:
            subprocess.run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", database,
                 "-n", schema, "-f", backup_path],
                check=True, capture_output=True, text=True,
                env={**os.environ, "PGPASSWORD": pg.get("password", "")}
            )
            return True, "PostgreSQL geri yükleme tamamlandı."
        except FileNotFoundError:
            return False, "psql bulunamadı."
        except subprocess.CalledProcessError as e:
            return False, f"Geri yükleme hatası: {e.stderr}"
    else:
        return False, "PostgreSQL için yedek .sql formatında olmalıdır."


def clean_old_backups(max_count=30):
    backups = list_backups()
    if len(backups) <= max_count:
        return
    backup_dir = get_backup_folder()
    if backup_dir is None:
        return
    for old in backups[max_count:]:
        try:
            os.remove(os.path.join(backup_dir, old))
        except Exception as e:
            print(f"Yedek silme hatası ({old}): {e}")
