"""Friendly Python entry point for the BHSim generator."""
from pathlib import Path
from .engine import Config, generate, validate, export_csv

class BHSimulator:
    """Generate linked synthetic behavioral health records (no PHI input)."""
    def __init__(self, clients=1000, employees=80, history_months=12,
                 future_days=30, reference_date="2026-10-10", seed=42):
        self.config = Config(clients=clients, employees=employees, months=history_months,
                             future_days=future_days, reference_date=reference_date, seed=seed)
        self.database_path = None

    def generate(self, path="behavioral_health.db"):
        self.database_path = Path(path)
        return generate(self.database_path, self.config)

    def to_sqlite(self, path=None):
        if self.database_path is None:
            raise RuntimeError("Call generate() first")
        if path is not None and Path(path).resolve() != self.database_path.resolve():
            import shutil
            shutil.copyfile(self.database_path, path)
            return Path(path)
        return self.database_path

    def to_csv(self, directory="output"):
        if self.database_path is None:
            raise RuntimeError("Call generate() first")
        return export_csv(self.database_path, directory)

    def validate(self):
        if self.database_path is None:
            raise RuntimeError("Call generate() first")
        return validate(self.database_path)
