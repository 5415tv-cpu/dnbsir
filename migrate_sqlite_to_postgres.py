import os
import sqlite3

import pandas as pd
from sqlalchemy import create_engine


SQLITE_DB = os.environ.get("SQLITE_DB", "database.db")
POSTGRES_DSN = os.environ.get("CLOUD_SQL_DSN") or os.environ.get("DATABASE_URL", "")


def _get_sqlite_conn():
    return sqlite3.connect(SQLITE_DB)


def _get_pg_engine():
    if not POSTGRES_DSN:
        raise RuntimeError("CLOUD_SQL_DSN or DATABASE_URL is required.")
    return create_engine(POSTGRES_DSN, pool_pre_ping=True)


def migrate_table(table_name: str) -> int:
    conn = _get_sqlite_conn()
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    except Exception:
        conn.close()
        return 0
    conn.close()

    if df.empty:
        return 0

    engine = _get_pg_engine()
    with engine.begin() as pg_conn:
        df.to_sql(table_name, pg_conn, if_exists="append", index=False)
    return len(df)


def main():
    tables = [
        "users",
        "stores",
        "orders",
        "wallet_logs",
        "wallet_topups",
        "sms_logs",
        "virtual_numbers",
        "couriers",
        "riders",
        "records_general",
        "records_delivery",
        "products",
        "reservations",
        "store_settings",
        "deliveries",
        "ledger_records",
    ]
    total = 0
    for table in tables:
        try:
            count = migrate_table(table)
            total += count
            print(f"{table}: {count} rows")
        except Exception as exc:
            print(f"{table}: failed ({exc})")
    print(f"Total migrated rows: {total}")


if __name__ == "__main__":
    main()
