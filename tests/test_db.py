import pytest

from app import db


def test_capabilities():
    caps = db.check_capabilities()
    assert caps["fts5"] and caps["rtree"] and caps["json1"]


def test_migrations_fts_rtree(tmp_path):
    path = tmp_path / "t.db"
    assert db.init_db(path) == [1, 2, 3, 4]
    assert db.init_db(path) == []                      # idempotent
    with db.get_conn(path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        conn.execute("INSERT INTO photos (file_hash, file_name, file_path, thumb_path, caption) "
                     "VALUES ('h1', 'a.jpg', 'x', 'y', 'a dog running on the beach')")
        pid = conn.execute("SELECT id FROM photos").fetchone()[0]
        db.refresh_fts(conn, pid)
        # porter stemming: "dogs" matches "dog"
        assert conn.execute("SELECT rowid FROM photos_fts WHERE photos_fts MATCH 'dogs'").fetchone()[0] == pid
        conn.execute("INSERT INTO geo_rtree VALUES (?, 48.85, 48.85, 2.35, 2.35)", (pid,))
        hits = conn.execute("SELECT id FROM geo_rtree WHERE min_lat >= 48 AND max_lat <= 49 "
                            "AND min_lon >= 2 AND max_lon <= 3").fetchall()
        assert [r[0] for r in hits] == [pid]
    assert db.haversine_km(48.8566, 2.3522, 51.5074, -0.1278) == pytest.approx(343.5, abs=5)