import pymysql
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Notes Service - DB Migration")
    parser.add_argument("--db-host", default="127.0.0.1")
    parser.add_argument("--db-port", type=int, default=3306)
    parser.add_argument("--db-user", required=True)
    parser.add_argument("--db-password", required=True)
    parser.add_argument("--db-name", required=True)
    return parser.parse_args()

MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS notes (
        id         INT UNSIGNED    NOT NULL AUTO_INCREMENT,
        title      VARCHAR(255)    NOT NULL,
        content    TEXT            NOT NULL,
        created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_notes_created_at
        ON notes (created_at DESC);
    """,
]


def run_migrations(conn: pymysql.connections.Connection) -> None:
    with conn.cursor() as cur:
        for sql in MIGRATIONS:
            cur.execute(sql.strip())
    conn.commit()
    print("[migrate] All migrations applied successfully.")


def main() -> None:
    args = parse_args()

    print(f"[migrate] Connecting to {args.db_host}:{args.db_port}/{args.db_name} ...")
    try:
        conn = pymysql.connect(
            host=args.db_host,
            port=args.db_port,
            user=args.db_user,
            password=args.db_password,
            database=args.db_name,
            charset="utf8mb4",
        )
    except pymysql.Error as exc:
        print(f"[migrate] ERROR: Cannot connect to database: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        run_migrations(conn)
    except pymysql.Error as exc:
        print(f"[migrate] ERROR: Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
