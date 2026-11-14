"""Create or upgrade the SQLite database and report engine capabilities."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db                 # noqa: E402
from app.config import settings    # noqa: E402


def main() -> None:
    caps = db.check_capabilities()
    print(f"SQLite {caps['sqlite_version']}  FTS5={caps['fts5']}  R*Tree={caps['rtree']}  JSON1={caps['json1']}")
    applied = db.init_db()
    print(f"Database : {settings.db_path}")
    print(f"Applied  : {applied or 'nothing (already up to date)'}")
    with db.get_conn() as conn:
        print("journal_mode =", conn.execute("PRAGMA journal_mode").fetchone()[0])
        for r in conn.execute("SELECT version, name, applied_at FROM schema_migrations ORDER BY version"):
            print(f"  v{r[0]}  {r[1]:<16} {r[2]}")


if __name__ == "__main__":
    main()