"""BHSim local Streamlit UI. Synthetic data only; no network calls."""
from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import date
from pathlib import Path
from uuid import uuid4

import streamlit as st

from bhsim import Config, generate, validate, export_csv

# ---SETUP---
st.set_page_config(page_title="BHSim", page_icon="▦", layout="wide")
st.title("BHSim")
st.caption("Synthetic behavioral health data for SQL and Power BI | Creator: Rahul Byrapuneni")
st.info("Fictional screening data only. PHQ-9 and GAD-7 totals are for testing, not diagnosis.")

# ---DATASET OPTIONS---
with st.sidebar:
    st.subheader("Dataset settings")
    clients = st.number_input("Fictional individuals", 10, 10000, 100, step=10,
                              help="Number of fictional people to generate.")
    employees = st.number_input("Employees", 2, 2000, 30, step=1,
                                help="Fictional employees who can work across multiple programs.")
    months = st.slider("Historical months", 1, 60, 12,
                       help="Months of historical visits and enrollment records.")
    future_days = st.slider("Future appointment days", 0, 180, 30,
                            help="Upcoming appointments are scheduled, not completed.")
    reference_date = st.date_input("Simulation reference date", value=date.today(),
                                   help="The fixed 'today' in this fictional dataset.")
    seed = st.number_input("Random seed", -1000000, 1000000, 42,
                           help="Same seed, settings, and code version reproduce the same dataset.")

# ---GENERATE AND EXPORT---
if st.button("Generate synthetic dataset", type="primary", use_container_width=True):
    with st.spinner("Generating and validating locally..."):
        # Keep output on disk instead of deleting a still-open SQLite database
        # during TemporaryDirectory cleanup (WinError 32 on Windows).
        run_dir = Path(__file__).resolve().parent / "generated" / f"run_{uuid4().hex[:12]}"
        db_path = run_dir / "behavioral_health.db"
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            settings = Config(
                int(clients), int(employees), int(months), int(future_days),
                reference_date.isoformat(), int(seed)
            )
            counts = generate(db_path, settings)
            result = validate(db_path)
            if not result["valid"]:
                st.error("Validation failed; no download will be offered.")
                st.json(result)
            else:
                csv_paths = export_csv(db_path, run_dir / "csv")
                csv_memory = io.BytesIO()
                with zipfile.ZipFile(csv_memory, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for csv_path in csv_paths:
                        archive.write(csv_path, arcname=Path(csv_path).name)
                with closing(sqlite3.connect(db_path)) as connection:
                    counts["assessment_scores"] = connection.execute(
                        "SELECT COUNT(*) FROM assessment_scores"
                    ).fetchone()[0]
                    counts["discharged_enrollments"] = connection.execute(
                        "SELECT COUNT(*) FROM individual_programs WHERE end_date IS NOT NULL"
                    ).fetchone()[0]
                    counts["no_show_visits"] = connection.execute(
                        "SELECT COUNT(*) FROM visits WHERE visit_status='NO_SHOW'"
                    ).fetchone()[0]
                st.session_state["bhsim_result"] = {
                    "counts": counts,
                    "db_bytes": db_path.read_bytes(),
                    "csv_bytes": csv_memory.getvalue(),
                    "config": {"seed": int(seed), "reference_date": str(reference_date)},
                    "saved_to": str(run_dir),
                }
        except Exception as exc:
            st.error(f"Generation failed: {exc}")
            st.caption(f"Any partial files remain in {run_dir} for troubleshooting. This folder can be deleted when BHSim is closed.")

# ---RESULTS---
if "bhsim_result" in st.session_state:
    result = st.session_state["bhsim_result"]
    st.success("Dataset generated and validated successfully.")
    stats = result["counts"]
    cols = st.columns(4)
    for column, (label, key) in zip(cols, [
        ("Individuals", "individuals"), ("Visits", "visits"),
        ("Assessments", "assessments"), ("Discharged enrollments", "discharged_enrollments"),
    ]):
        column.metric(label, f"{stats.get(key, 0):,}")
    st.caption(
        "Visits include completed and noncompleted appointments. "
        "Discharged enrollments are enrollment episodes that ended."
    )
    left, right = st.columns(2)
    with left:
        st.download_button("Download SQLite database", data=result["db_bytes"],
                           file_name="behavioral_health.db", mime="application/vnd.sqlite3",
                           use_container_width=True)
    with right:
        st.download_button("Download all CSV tables (ZIP)", data=result["csv_bytes"],
                           file_name="behavioral_health_csv.zip", mime="application/zip",
                           use_container_width=True)
    with st.expander("Dataset information and local files"):
        st.json({"records": stats, "settings": result["config"]})
        st.code(result["saved_to"], language="text")
        st.caption("Generated files are saved on your computer. To reclaim space, close BHSim and delete old run folders under BHSim/generated.")
else:
    st.write("Choose your settings and click **Generate synthetic dataset**. Everything runs locally; no patient data or API key is required.")

st.divider()
st.caption("Preview release: not for clinical decisions, billing, or research inference. Synthetic patterns are illustrative assumptions.")
