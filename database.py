# database.py
# Compatibility layer - delegates to connection_manager.py

from connection_manager import (
    get_session,
    set_database,
    get_current_db_path,
    get_db_folder,
    get_current_firma,
    get_db_type,
    load_config,
    save_config,
    init_sqlite,
    init_postgresql,
    test_postgresql_connection,
    list_pg_schemas,
    keepalive,
)


def get_engine():
    from connection_manager import _engine
    return _engine
