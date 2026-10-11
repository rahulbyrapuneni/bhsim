# BHSim

**Synthetic behavioral health data for SQL, analytics, and application testing.**

[![PyPI version](https://img.shields.io/pypi/v/bhsim?label=PyPI)](https://pypi.org/project/bhsim/)
[![Python versions](https://img.shields.io/pypi/pyversions/bhsim)](https://pypi.org/project/bhsim/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Actions](https://github.com/rahulbyrapuneni/bhsim/actions/workflows/tests.yml/badge.svg)](https://github.com/rahulbyrapuneni/bhsim/actions)

**[Install from PyPI](https://pypi.org/project/bhsim/) · [Source code](https://github.com/rahulbyrapuneni/bhsim) · [Report an issue](https://github.com/rahulbyrapuneni/bhsim/issues)**

BHSim is an open-source Python library that generates **fictional, interconnected behavioral health records**. It gives analysts, developers, students, and educators a ready-to-query dataset without asking them to find or handle real patient information.

In a few lines of Python, you can create a SQLite database containing individuals, programs, enrollments, employees, appointments, productivity records, and screening assessments. Use it to practice SQL joins, prototype Power BI dashboards, develop analytics features, or test software that expects relational healthcare-style data.

> **Release status:** `1.0.0rc2` is a public **release candidate**. Install this specific version using the command below. BHSim is intended for development, demonstrations, and education—not clinical decisions, official quality reporting, or billing.

## Why BHSim?

Sample spreadsheets are useful for learning individual SQL queries, but real analytics often depends on **relationships between records**. An individual may participate in several programs, a staff member may serve multiple programs, and each appointment must connect to the right people and enrollment history.

BHSim generates those relationships for you, so you can spend more time learning, querying, building, and testing—and less time assembling fake data by hand.

**Common uses:**

- **SQL practice:** Join visits with individuals, employees, programs, and enrollments.
- **BI dashboards:** Explore attendance, no-shows, program activity, staff workload, and screening trends.
- **Application testing:** Test database queries, ETL pipelines, APIs, and analytics features with fictional records.
- **Teaching and portfolio projects:** Demonstrate healthcare-style reporting without sharing protected health information (PHI).

## Install

**Requirements:** Python 3.10 or newer. No database server, paid service, or patient dataset is required.

Install the published release candidate from [PyPI](https://pypi.org/project/bhsim/):

```bash
python -m pip install bhsim==1.0.0rc2
```

On Windows, you can use `py -m pip` in place of `python -m pip`.

> **Why specify the version?** PyPI currently hosts a release candidate. Specifying `1.0.0rc2` ensures pip selects it even when prereleases are not normally included.

## Generate your first dataset

Create a file called `example.py`:

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

Run it:

```bash
python example.py
```

You will get:

- **`behavioral_health.db`** — a SQLite database with related synthetic tables.
- **`output/`** — CSV exports you can load into spreadsheets or BI tools.
- **Validation results** — a report checking the dataset's core consistency rules. A passing result includes `"valid": true` and an empty `issues` list.

**Note:** BHSim does not overwrite an existing database file. Use a new filename if you want to generate another dataset.

### Prefer a command-line workflow?

```bash
python -m bhsim generate demo.db --clients 100 --seed 42
python -m bhsim validate demo.db
python -m bhsim export-csv demo.db output
```

You can also use the installed `bhsim` command when it is available on your system's PATH.

## What's inside the database?

| Area | Tables | What you'll find |
| --- | --- | --- |
| Individuals and programs | `individuals`, `programs`, `individual_programs` | Fictional people, MH/SA/IDD programs, admissions, discharges, and re-enrollments |
| Workforce | `employees`, `employee_programs`, `employee_supervision` | Staff members, program assignments, and reporting relationships |
| Appointments | `visits`, `visit_types`, `locations` | Scheduled and completed visits, no-shows, cancellations, rescheduling, and service times |
| Productivity | `productivity_rules`, `visit_productivity` | Illustrative productivity rules and visit-linked units |
| Screening assessments | `assessment_instruments`, `assessment_questions`, `answer_options`, `assessments`, `assessment_responses`, `assessment_scores` | PHQ-9 and GAD-7 items, answer options, responses, and scores |
| Generation details | `simulation_metadata` | Information about the simulation run |

There is also an **`assessment_responses_readable`** SQL view that brings together assessment questions and selected answers.

Records use primary and foreign keys. IDs are fixed-width, numeric-looking **text** values—not sequential row numbers. Names can repeat, so use IDs rather than names for joins.

## Explore your data with SQL

Open `behavioral_health.db` in a SQLite-compatible tool such as [SQLime](https://sqlime.org/), DB Browser for SQLite, or Python's built-in `sqlite3` module.

### 1. Appointments by program

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

**What it tells you:** Which programs have the most scheduled activity, completed appointments, and no-shows.

### 2. No-show rate by program

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

**What it tells you:** The percentage of eligible appointments marked as no-shows. This example uses **completed + no-show** visits as the denominator; actual organizations may define their reporting measures differently.

### 3. Visit history with individual and employee names

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

**What it tells you:** How appointments connect to the individual receiving services, the program, and the assigned employee.

### 4. Explore PHQ-9 and GAD-7 responses

```sql
SELECT
    instrument_code,
    question_text,
    selected_answer,
    score_value
FROM assessment_responses_readable
LIMIT 20;
```

**What it tells you:** Readable questions, answer choices, and simulated response scores, without writing several joins yourself.

PHQ-9 has nine scored items (complete total **0–27**), while GAD-7 has seven (complete total **0–21**). Incomplete submissions do not have complete total scores. These are simulated screening responses, **not diagnoses or clinically validated trajectories**.

## Customize your simulation

| Python argument | Example | Meaning |
| --- | --- | --- |
| `clients` | `1000` | Number of fictional individuals |
| `employees` | `80` | Number of fictional staff members |
| `history_months` | `12` | Historical period to simulate |
| `future_days` | `30` | Number of days of future appointments |
| `reference_date` | `"2026-10-10"` | Reference date in `YYYY-MM-DD` format |
| `seed` | `42` | Random seed for repeatable results |

Using the same version, settings, and seed produces a reproducible simulation. Change the seed to produce a different fictional dataset.

Some operational assumptions—including program hours, probabilities, and productivity calculations—are predefined in this release rather than exposed as user settings.

## Check data quality

BHSim includes built-in validation:

```bash
python -m bhsim validate demo.db
```

You can also independently inspect a SQLite database with a few simple queries.

**Check broken foreign-key relationships** (expected: no rows):

```sql
PRAGMA foreign_key_check;
```

**Check completed visits with missing or invalid service times** (expected: `0`):

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

**Check visits without a matching enrollment** (expected: `0` under the current simulation rules):

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

These checks validate **structural and business-rule consistency**. They do not demonstrate that the generated rates or outcomes represent real behavioral health populations.

## Use BHSim with Power BI

1. Generate the data and export it to CSV using `sim.to_csv("output")`.
2. In Power BI Desktop, select **Get data → Text/CSV** and load the files you need.
3. Use the ID columns to create relationships between individuals, visits, programs, and employees.
4. Build visuals for program activity, appointment statuses, staff productivity, or assessment trends.

You can also access SQLite directly through a compatible connector or ODBC configuration, if you prefer not to export CSV files.

## Develop and contribute

Clone the repository and install development dependencies:

```bash
git clone https://github.com/rahulbyrapuneni/bhsim.git
cd bhsim
python -m pip install -e ".[dev]"
python -m pytest -q
```

The main library lives in `src/bhsim/`. An **optional** Streamlit demo is available in the repository:

```bash
python -m pip install -e ".[ui]"
python -m streamlit run app.py
```

The demo is not required to install or use BHSim as a Python library.

Suggestions, bug reports, documentation improvements, and pull requests are welcome through [GitHub Issues](https://github.com/rahulbyrapuneni/bhsim/issues). Please **never submit real patient information or PHI** in issues, sample files, or tests.

## Important limitations

- **Synthetic, not sourced from patients:** BHSim generates fictional records and does not retrieve information from electronic health records.
- **Not a clinical model:** Demographic distributions, attendance behavior, utilization, and assessment trends are illustrative—not validated predictions of real populations.
- **Not for care decisions:** PHQ-9 and GAD-7 outputs must not be used for diagnosis, clinical decision support, or treatment recommendations.
- **Not billing guidance:** Productivity rules and units are examples, not payer-approved reimbursement logic.
- **Simplified workflows:** The current scheduling and program-enrollment rules do not cover every real-world exception or organization-specific workflow.
- **Schema versions matter:** Existing databases are not migrated automatically. Current releases use `full_name`; older generated datasets may contain `synthetic_name`.
- **Assessment rights:** Questionnaire wording and instrument-related rights belong to their respective owners. Confirm any applicable usage or redistribution requirements, particularly for clinical or commercial uses.

## License and credits

BHSim is open-source software released under the [MIT License](LICENSE). Third-party assessment rights and attribution are separate from the software license.

**Creator and maintainer:** [Rahul Byrapuneni](https://github.com/rahulbyrapuneni)

Created with behavioral health analytics domain direction and AI-assisted software development.

**Links:** [PyPI](https://pypi.org/project/bhsim/) · [GitHub](https://github.com/rahulbyrapuneni/bhsim) · [Issues](https://github.com/rahulbyrapuneni/bhsim/issues)
