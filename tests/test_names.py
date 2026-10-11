import sqlite3

from bhsim import BHSimulator


def test_human_readable_names_and_schema(tmp_path):
    db = tmp_path / "names.db"
    sim = BHSimulator(clients=300, employees=40, seed=42)
    sim.generate(db)
    assert sim.validate()["valid"] is True
    with sqlite3.connect(db) as con:
        for table in ("individuals", "employees"):
            columns = [row[1] for row in con.execute(f"PRAGMA table_info({table})")]
            assert "full_name" in columns
            assert "synthetic_name" not in columns
            names = [row[0] for row in con.execute(f"SELECT full_name FROM {table}")]
            assert names
            assert all(" #" not in name and "Staff #" not in name for name in names)
            assert all(len(name.split()) >= 2 for name in names)
        assert con.execute("SELECT COUNT(DISTINCT full_name) FROM individuals").fetchone()[0] > 100


def test_name_columns_in_csv(tmp_path):
    db = tmp_path / "csv_names.db"
    sim = BHSimulator(clients=30, employees=10, seed=99)
    sim.generate(db)
    sim.to_csv(tmp_path / "csv")
    for table in ("individuals", "employees"):
        header = (tmp_path / "csv" / f"{table}.csv").read_text(encoding="utf-8").splitlines()[0]
        assert "full_name" in header.split(",")
        assert "synthetic_name" not in header
