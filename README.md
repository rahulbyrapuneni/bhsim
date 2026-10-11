# BHSim

### Synthetic behavioral health data, ready for SQL and analytics

BHSim is an open-source Python library that creates **fictional, connected behavioral health records** for SQL practice, BI dashboards, software testing, and analytics prototypes.

Instead of hand-building spreadsheets or borrowing sensitive patient data, you can generate a small SQLite database with clients, programs, staff, appointments, enrollments, and screening assessments—and start querying it right away.

**Created and maintained by Rahul Byrapuneni.**

> **Important:** BHSim generates synthetic test data, not real patient records. Its scheduling, attendance, assessment trajectories, and productivity assumptions are examples for development and learning—not clinical predictions, diagnostic advice, official reporting definitions, or billing guidance.

## What can BHSim generate?

- **Individuals:** Fictional names, dates of birth, demographic fields, and unique numeric identifiers.
- **Programs:** Mental health (MH), substance use (SA), and intellectual/developmental disabilities (IDD) services.
- **Enrollments:** Admissions, discharges, multiple concurrent programs, and re-enrollment histories.
- **Employees:** Staff records, program assignments, and supervisor relationships.
- **Visits:** Completed, no-show, canceled, rescheduled, and upcoming appointments, with scheduled and actual service times.
- **Productivity:** Example service-unit calculations linked to visits and program rules.
- **Assessments:** PHQ-9 and GAD-7 with readable question text, answer choices, responses, and total scores for complete assessments.

The records are linked through primary and foreign keys, so you can practice realistic joins without needing access to an EHR.

## Quick start

**Requirements:** Python 3.10 or newer. No database server, paid API, or patient data is needed.

BHSim is currently available from its GitHub repository. To install it directly:

```bash
python -m pip install git+https://github.com/rahulbyrapuneni/bhsim.git
```

> PyPI publication is planned, but **`pip install bhsim` is not yet the documented installation method**.

Create a file named `example.py`:

```python
from bhsim import BHSimulator

# ---SET UP A SYNTHETIC ORGANIZATION---
sim = BHSimulator(
    clients=1000,
    employees=80,
    history_months=12,
    future_days=30,
    seed=42,
)

# ---GENERATE, CHECK, AND EXPORT---
sim.generate("behavioral_health.db")
print(sim.validate())
sim.to_csv("output")
```

Run:

```bash
python example.py
```

You'll get `behavioral_health.db` plus a folder of CSV files, one for each table. A successful validation returns a result with `"valid": true` and an empty `issues` list.

**Already have an output database?** BHSim deliberately refuses to overwrite it. Choose a new filename or move the old one before generating another dataset.

### Prefer the command line?

```bash
python -m bhsim generate demo.db --clients 100 --seed 42
python -m bhsim validate demo.db
python -m bhsim export-csv demo.db output
```

The installed `bhsim` command can be used instead of `python -m bhsim` when it is available on your PATH.

## Explore the data with SQL

You can open the generated `.db` file with a SQLite-compatible editor, including [SQLime](https://sqlime.org/), or use Python's built-in `sqlite3` library.

### Appointments by program

```sql
SELECT
    p.program_code,
    p.description AS program_name,
    COUNT(*) AS appointments,
    SUM(CASE WHEN v.visit_status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN v.visit_status = 'NO_SHOW' THEN 1 ELSE 0 END) AS no_shows
FROM visits AS v
JOIN programs AS p ON p.program_id = v.program_id
GROUP BY p.program_code, p.description
ORDER BY appointments DESC;
```

### No-show rate by program

```sql
SELECT
    p.program_code,
    COUNT(*) AS eligible_appointments,
    SUM(CASE WHEN v.visit_status = 'NO_SHOW' THEN 1 ELSE 0 END) AS no_shows,
    ROUND(
        100.0 * SUM(CASE WHEN v.visit_status = 'NO_SHOW' THEN 1 ELSE 0 END)
        / COUNT(*), 2
    ) AS no_show_pct
FROM visits AS v
JOIN programs AS p ON p.program_id = v.program_id
WHERE v.visit_status IN ('COMPLETED', 'NO_SHOW')
GROUP BY p.program_code
ORDER BY no_show_pct DESC;
```

This example uses **completed + no-show** visits as its denominator. Organizations may define reportable no-show measures differently.

### Individual visit history

```sql
SELECT
    i.individual_id,
    i.full_name,
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

### Read actual assessment questions and selected answers

BHSim keeps question text and answer choices in lookup tables instead of repeating them in every response. The built-in view joins those tables for you:

```sql
SELECT
    instrument_code,
    question_text,
    selected_answer,
    score_value
FROM assessment_responses_readable
LIMIT 20;
```

PHQ-9 contains nine scored symptom items (complete total: **0–27**); GAD-7 contains seven (complete total: **0–21**). Incomplete assessments do not receive a complete total. Scores in BHSim are simulated screening data, **not diagnoses**.

## How the tables fit together

| Area | Tables | What they represent |
|---|---|---|
| People and programs | `individuals`, `programs`, `individual_programs` | Individuals and their enrollment episodes |
| Workforce | `employees`, `employee_programs`, `employee_supervision` | Staff assignments and reporting relationships |
| Services | `visits`, `visit_types`, `locations` | Scheduled appointments and documented services |
| Productivity | `productivity_rules`, `visit_productivity` | Example rules and calculated units |
| Assessments | `assessment_instruments`, `assessment_questions`, `answer_options`, `assessments`, `assessment_responses`, `assessment_scores` | Forms, questions, selected answers, and scored submissions |
| Supporting data | `simulation_metadata` | Configuration and generation metadata |

There is also an `assessment_responses_readable` **SQL view** for simpler queries.

Identifiers are numeric-looking **TEXT** values, with fixed lengths defined by entity type. They are deliberately nonsequential and are joined by ID, not by name. Names may repeat, just as they can in real records.

## Customize a run

These are the main settings available through the Python API:

| Parameter | Example | Meaning |
|---|---|---|
| `clients` | `1000` | Number of fictional individuals |
| `employees` | `80` | Number of fictional staff records |
| `history_months` | `12` | Historical period to simulate |
| `future_days` | `30` | Days of upcoming appointments |
| `reference_date` | `"2026-10-10"` | Simulation's reference date, in `YYYY-MM-DD` format |
| `seed` | `42` | Controls the pseudorandom sequence for reproducibility |

**What is a seed?** With the same BHSim code, settings, and seed, generation is reproducible. Change the seed to get a different fictional dataset. The number `42` has no special meaning.

Some program-specific probabilities, operating hours, and productivity assumptions are currently defined internally rather than exposed as configurable API options.

## Data checks

BHSim includes a validator for core integrity rules:

```bash
python -m bhsim validate demo.db
```

You can also run these independent SQLite checks:

```sql
-- Broken foreign keys: expect no rows
PRAGMA foreign_key_check;

-- Completed visits without valid service timestamps: expect zero
SELECT COUNT(*) AS invalid_completed_visits
FROM visits
WHERE visit_status = 'COMPLETED'
  AND (actual_start IS NULL OR actual_end IS NULL
       OR actual_end <= actual_start);

-- Visits without a matching program enrollment: expect zero
SELECT COUNT(*) AS visits_outside_enrollment
FROM visits AS v
WHERE NOT EXISTS (
    SELECT 1
    FROM individual_programs AS ip
    WHERE ip.individual_id = v.individual_id
      AND ip.program_id = v.program_id
      AND DATE(v.scheduled_start) >= DATE(ip.start_date)
      AND (ip.end_date IS NULL OR DATE(v.scheduled_start) <= DATE(ip.end_date))
);
```

Validation checks **consistency**, not whether the generated statistics match real healthcare populations.

## Contributing and developing locally

```bash
git clone https://github.com/rahulbyrapuneni/bhsim.git
cd bhsim
python -m pip install -e ".[dev]"
python -m pytest -q
```

The library's main code lives under `src/bhsim/`. `app.py` is an **optional Streamlit demonstration**; it is not needed for library installation or use. To run the demo, install the optional UI dependencies with `python -m pip install -e ".[ui]"`, then use `python -m streamlit run app.py`.

Contributions that improve documentation, validation, reproducibility, or realistic *synthetic* workflows are welcome. Please don't submit real patient records or other protected health information in issues, examples, or tests.

## Limitations and responsible use

- All records are fictional. BHSim does **not** access EHRs or require patient data.
- Generated distributions are illustrative; the library has not been validated as a model of real-world clinical outcomes, demographics, or utilization.
- PHQ-9 and GAD-7 are screening instruments. Simulated scores are not diagnoses, treatment recommendations, or a substitute for clinical judgment.
- Visit eligibility currently assumes a matching enrollment episode; un-enrolled crisis-service exceptions are not generated in this release.
- Scheduling checks cover completed-service conflicts, not every possible appointment-booking workflow.
- Productivity units use demonstration rules and should not be treated as reimbursement or billing guidance.
- Existing databases are not automatically migrated when the schema changes. Newer releases use `full_name` in place of the older `synthetic_name` column.
- Questionnaire wording and names belong to their respective instrument originators. Preserve attribution and confirm the relevant usage terms before redistributing or using the instruments clinically.

## License and author

BHSim is released under the [MIT License](LICENSE). See the repository's `LICENSE` file for its full terms. Instrument attribution and third-party rights are separate from the project's software license.

**Creator & maintainer:** [Rahul Byrapuneni](https://github.com/rahulbyrapuneni)  
**Repository:** [github.com/rahulbyrapuneni/bhsim](https://github.com/rahulbyrapuneni/bhsim)

Developed using AI-assisted software engineering, with behavioral health domain direction and product design led by the creator.
