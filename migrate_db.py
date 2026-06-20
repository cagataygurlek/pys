import sqlite3
from sqlalchemy import inspect
from database import get_engine
from models import Base


def add_columns():
    engine = get_engine()
    db_url = str(engine.url)
    if not db_url.startswith("sqlite:///"):
        return

    db_path = db_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    inspector = inspect(engine)

    for table_name in inspector.get_table_names():
        try:
            existing = {col["name"] for col in inspector.get_columns(table_name)}
        except Exception:
            continue

        try:
            mapper = next(
                m for m in Base.registry.mappers
                if m.class_.__tablename__ == table_name
            )
        except StopIteration:
            continue

        for col_name, col_prop in mapper.columns.items():
            if col_name not in existing:
                col_type = "FLOAT"
                if hasattr(col_prop.type, "length") and isinstance(col_prop.type.length, int):
                    col_type = f"VARCHAR({col_prop.type.length})"
                elif "Integer" in type(col_prop.type).__name__:
                    col_type = "INTEGER"
                elif "String" in type(col_prop.type).__name__ or "Text" in type(col_prop.type).__name__:
                    length = getattr(col_prop.type, "length", None)
                    col_type = f"VARCHAR({length})" if length else "TEXT"
                elif "Date" in type(col_prop.type).__name__:
                    col_type = "DATE"
                elif "Boolean" in type(col_prop.type).__name__:
                    col_type = "INTEGER DEFAULT 0"

                default = ""
                if col_prop.default is not None and col_prop.default.is_scalar:
                    default_val = col_prop.default.arg
                    default = f" DEFAULT {default_val}"

                nullable = "" if col_prop.nullable else " NOT NULL"

                try:
                    cursor.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}{default}{nullable}"
                    )
                    print(f"   + {table_name}.{col_name} ({col_type})")
                except Exception as e:
                    pass

    conn.commit()
    conn.close()


if __name__ == "__main__":
    add_columns()
