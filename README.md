<p align="center">
  <img src="https://raw.githubusercontent.com/rahulbyrapuneni/bhsim/main/assets/bhsim-banner.png"
       alt="BHSim - Python library for synthetic behavioral health data"
       width="850">
</p>

<p align="center">
  <a href="https://pypi.org/project/bhsim/"><img src="https://img.shields.io/badge/PyPI-bhsim-245A81" alt="BHSim on PyPI"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-245A81" alt="Python 3.10 or newer">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-245A81" alt="MIT License"></a>
  <a href="https://github.com/rahulbyrapuneni/bhsim/actions/workflows/tests.yml"><img src="https://github.com/rahulbyrapuneni/bhsim/actions/workflows/tests.yml/badge.svg" alt="Automated tests"></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/bhsim/">PyPI</a> ·
  <a href="https://github.com/rahulbyrapuneni/bhsim/releases">Releases</a> ·
  <a href="https://github.com/rahulbyrapuneni/bhsim/issues">Report an issue</a>
</p>

BHSim is an open-source Python library for creating **synthetic behavioral health data**. It generates fictional but connected records for individuals, programs, employees, appointments, productivity, and screening assessments, then saves them in a SQLite database you can query immediately.

The goal is simple: make it easier to learn, build, and test behavioral health analytics without needing access to real patient information.

## Why BHSim?

A spreadsheet of random names and dates is fine for a basic exercise. It becomes less useful when you need to answer questions across several tables: Which programs have the highest no-show rates? How many appointments did an employee complete? How did an individual's assessment scores change over time?

BHSim gives those records meaningful connections. Individuals can enroll in multiple programs, employees can work across programs, and visits are linked to the relevant people and services. You can focus on the query, dashboard, or application you're building instead of assembling test data by hand.

BHSim is useful for SQL practice, Power BI prototypes, analytics development, teaching, portfolio work, and testing data pipelines or applications that use relational records.

## Installation

BHSim requires **Python 3.10 or newer** and is available on [PyPI](https://pypi.org/project/bhsim/).

```bash
pip install bhsim
```

No database server, paid API, or real patient dataset is required.

## Quick start

Create a Python file, such as `example.py`:

```python
from bhsim import BHSimulator

sim = BHSimulator(
    clients=1000,
    employees=80,
    history_months=12,
    future_days=30,
    seed=42,
)

sim.generate("behavioral_health.db")
print(sim.validate())
sim.to_csv("output")
```

Run it with:

```bash
python example.py
```

You'll have:

- **`behavioral_health.db`** — a SQLite database with related tables and sample records.
- **`output/`** — CSV exports for Excel, Power BI, or other tools.
- **A validation result** — the output of `sim.validate()`. A successful check returns `{'valid': True, 'issues': []}`.

BHSim will not overwrite an existing database file. Choose a new filename when generating another dataset.

### Command-line usage

You can generate, validate, and export data without writing a Python script:

```bash
python -m bhsim generate demo.db --clients 100 --seed 42
python -m bhsim validate demo.db
python -m bhsim export-csv demo.db output
```

## What does BHSim generate?

| Area | Main tables | Contents |
| --- | --- | --- |
| Individuals and programs | `individuals`, `programs`, `individual_programs` | Fictional individuals, behavioral health programs, and enrollment histories |
| Workforce | `employees`, `employee_programs`, `employee_supervision` | Employee assignments and reporting relationships |
| Appointments | `visits`, `visit_types`, `locations` | Completed visits, no-shows, cancellations, rescheduling, and scheduled appointments |
| Productivity | `productivity_rules`, `visit_productivity` | Illustrative productivity rules and visit-level activity |
| Screening assessments | `assessment_instruments`, `assessment_questions`, `answer_options`, `assessments`, `assessment_responses`, `assessment_scores` | PHQ-9 and GAD-7 questions, responses, and scores |
| Simulation details | `simulation_metadata` | Information about the dataset generation run |

The database also includes an `assessment_responses_readable` view so you can see assessment questions and selected answers without writing several joins.

Tables are connected through primary and foreign keys. Identifiers are fixed-width, numeric-looking strings. **Join on IDs, not names**: different fictional people may have the same name.

## Try a few SQL queries

Open `behavioral_health.db` in a SQLite-compatible tool, such as [SQLime](https://sqlime.org/), DB Browser for SQLite, or Python's `sqlite3` module.

### Appointments by program

See how appointment activity differs across programs:

```sql
SELECT
    p.program_code,
    p.description AS program_name,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN v.visit_status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN v.visit_status = 'NO_SHOW' THEN 1 ELSE 0 END) AS no_shows
FROM visits AS v
JOIN programs AS p
    ON p.program_id = v.program_id
GROUP BY p.program_code, p.description
ORDER BY total_appointments DESC;
```

### No-show rate by program

This example uses completed and no-show visits as the denominator. Your organization may define this metric differently.

```sql
SELECT
    p.program_code,
    COUNT(*) AS eligible_appointments,
    SUM(CASE WHEN v.visit_status = 'NO_SHOW' THEN 1 ELSE 0 END) AS no_shows,
    ROUND(
        100.0 * SUM(CASE WHEN v.visit_status = 'NO_SHOW' THEN 1 ELSE 0 END)
        / COUNT(*),
        2
    ) AS no_show_percentage
FROM visits AS v
JOIN programs AS p
    ON p.program_id = v.program_id
WHERE v.visit_status IN ('COMPLETED', 'NO_SHOW')
GROUP BY p.program_code
ORDER BY no_show_percentage DESC;
```

### See who was scheduled for a visit

```sql
SELECT
    i.individual_id,
    i.full_name AS individual_name,
    p.program_code,
    v.visit_status,
    v.scheduled_start,
    e.full_name AS employee_name
FROM visits AS v
JOIN individuals AS i ON i.individual_id = v.individual_id
JOIN programs AS p ON p.program_id = v.program_id
JOIN employees AS e ON e.employee_id = v.employee_id
ORDER BY v.scheduled_start DESC
LIMIT 20;
```

### Read PHQ-9 and GAD-7 responses

```sql
SELECT
    instrument_code,
    question_text,
    selected_answer,
    score_value
FROM assessment_responses_readable
LIMIT 20;
```

BHSim includes simulated PHQ-9 (nine scored questions; complete score range 0–27) and GAD-7 (seven scored questions; complete score range 0–21) responses. These values are for testing and demonstration, **not clinical interpretation**.

## Adjust the dataset

You can change the size, time period, or random seed when creating a simulator.

| Argument | Example | Purpose |
| --- | --- | --- |
| `clients` | `1000` | Number of fictional individuals |
| `employees` | `80` | Number of fictional staff members |
| `history_months` | `12` | Length of simulated history |
| `future_days` | `30` | Days of future scheduled appointments |
| `reference_date` | `"2026-10-10"` | Reference date in `YYYY-MM-DD` format |
| `seed` | `42` | Controls reproducibility |

Using the same BHSim version, settings, and seed produces reproducible data. Changing the seed produces a different dataset.

Some assumptions, including program hours and productivity calculations, are built into the current simulator rather than configurable through the public API.

## Checking data quality

BHSim includes a built-in validator:

```python
print(sim.validate())
```

You can also validate a saved database from the command line:

```bash
python -m bhsim validate behavioral_health.db
```

For an independent check, try these SQL queries.

**Foreign-key integrity** — expect no rows:

```sql
PRAGMA foreign_key_check;
```

**Completed appointments with missing or invalid service times** — expect `0`:

```sql
SELECT COUNT(*) AS invalid_completed_visits
FROM visits
WHERE visit_status = 'COMPLETED'
  AND (
      actual_start IS NULL
      OR actual_end IS NULL
      OR actual_end <= actual_start
  );
```

**Visits without a matching program enrollment** — expect `0` under the current simulation rules:

```sql
SELECT COUNT(*) AS visits_outside_enrollment
FROM visits AS v
WHERE NOT EXISTS (
    SELECT 1
    FROM individual_programs AS ip
    WHERE ip.individual_id = v.individual_id
      AND ip.program_id = v.program_id
      AND DATE(v.scheduled_start) >= DATE(ip.start_date)
      AND (
          ip.end_date IS NULL
          OR DATE(v.scheduled_start) <= DATE(ip.end_date)
      )
);
```

These tests check data relationships and defined business rules. They do **not** establish that generated attendance rates, diagnoses, or assessment patterns match real populations.

## Working with Power BI

If you're building a Power BI report, the easiest path is to export the database to CSV:

1. Run `sim.to_csv("output")` after generating your dataset.
2. In Power BI Desktop, use **Get data → Text/CSV** to load the tables you need.
3. Connect the tables using their ID columns.
4. Explore appointment outcomes, program activity, productivity, or assessment trends.

You can also use a suitable SQLite connector or ODBC configuration instead of CSV exports.

## Development and contributions

To run BHSim from source:

```bash
git clone https://github.com/rahulbyrapuneni/bhsim.git
cd bhsim
python -m pip install -e ".[dev]"
python -m pytest -q
```

The library code is in `src/bhsim/`. The repository also contains an optional Streamlit demo:

```bash
python -m pip install -e ".[ui]"
python -m streamlit run app.py
```

The demo is optional; you don't need Streamlit to use the Python library.

Issues, bug reports, documentation corrections, and pull requests are welcome. Open an [issue](https://github.com/rahulbyrapuneni/bhsim/issues) if something isn't working or you have an idea worth discussing. Please do not include real patient data or other sensitive information in sample files, issues, or contributions.

## Scope and limitations

BHSim creates fictional data for education, development, and analytics testing. It does not connect to an EHR or use actual patient records.

The generated population, service patterns, and assessment responses are illustrative. They should not be treated as statistically representative of a real community or organization. BHSim is **not** intended for diagnosis, treatment decisions, clinical decision support, official quality reporting, or reimbursement calculations. Productivity units are examples, not payer billing rules.

The data model simplifies some real-world workflows. Existing generated databases are not migrated automatically between schema versions; if you need the latest schema, generate a new dataset. In particular, current versions use `full_name`, whereas older datasets may contain `synthetic_name`.

PHQ-9 and GAD-7 instrument wording and related rights remain with their respective owners. The MIT License for BHSim's software does not grant additional rights to third-party assessment materials; verify applicable requirements before redistribution or commercial use.

## License and author

BHSim is released under the [MIT License](LICENSE).

**Created and maintained by [Rahul Byrapuneni](https://github.com/rahulbyrapuneni).** Developed with behavioral health analytics domain input and AI-assisted implementation.

[PyPI](https://pypi.org/project/bhsim/) · [Source code](https://github.com/rahulbyrapuneni/bhsim) · [Releases](https://github.com/rahulbyrapuneni/bhsim/releases) · [Issues](https://github.com/rahulbyrapuneni/bhsim/issues)
