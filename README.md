# BHSim — Synthetic Behavioral Health Data Library

**Creator & maintainer:** Rahul Byrapuneni  
**Status:** v1.0.0 release candidate; synthetic data for analytics/testing, **not clinical validation**.

BHSim produces connected fictional individuals, MH/SA/IDD programs, employee assignments, program enrollment episodes, scheduled/completed/no-show/rescheduled visits, productivity, and longitudinal PHQ-9/GAD-7 screening data. No EHR access, real PHI, or paid APIs are necessary.

## Install locally

Python 3.10+:

```powershell
py -m pip install -e ".[dev]"
```

## Python API (primary interface)

```python
from bhsim import BHSimulator

sim = BHSimulator(clients=1000, employees=80, history_months=12, seed=42)
sim.generate("behavioral_health.db")
print(sim.validate())
sim.to_csv("output")
```

The library intentionally refuses to overwrite existing SQLite files. Use a fresh filename for another run.

## Command line

```powershell
py -m bhsim generate demo.db --clients 100 --seed 42
py -m bhsim validate demo.db
py -m bhsim export-csv demo.db output
py -m pytest -q
```

## Readable assessment answers

Question text, scoring options, and responses are normalized in `assessment_questions`, `answer_options`, and `assessment_responses` tables. A convenience SQLite view joins them:

```sql
SELECT instrument_code, question_text, selected_answer, score_value
FROM assessment_responses_readable LIMIT 20;
```

The standard PHQ-9 and GAD-7 contain 9 and 7 frequency items. Scores sum item values for **complete** responses only (PHQ-9: 0–27; GAD-7: 0–21). An incomplete screening has **no total score**. The generator's response trajectories, no-show probabilities, staffing patterns, and productivity rates are synthetic assumptions; they are not clinical models, billing rules, or diagnostic output. PHQ-9 item 9 includes self-harm wording, solely as a standard screening item.

## Package design

- `bhsim.BHSimulator`: importable Python interface
- `bhsim.engine`: deterministic SQLite generation and validation
- `bhsim.cli`: command-line support
- `app.py`: optional Streamlit preview, not required to use the library

## Development

```powershell
py -m pip install -e ".[dev]"
py -m pytest -q
```

## Known limitations

- Synthetic operational patterns are plausible test fixtures, not epidemiological estimates.
- The v1 engine retains a conservative enrollment requirement for visits; no un-enrolled crisis encounters are simulated yet.
- Staffing overlap validation covers completed services; the model is not a full appointment-booking system.
- Program hours and productivity configuration currently live in the engine, rather than a public configuration file.
- PHQ-9/GAD-7 questionnaire text should retain attribution to their original instrument authors in any redistribution. Consult the instrument usage policies for intended clinical uses.

## Names and identifiers

Individuals and employees have a readable `full_name` field. Names are invented by combining
first and last names from built-in lists. They can repeat; **IDs, not names, are the keys**.
The database contains no real patient records. This release renames `synthetic_name` to
`full_name` in new outputs, so SQL written for the previous release must be updated.

```sql
SELECT i.individual_id, i.full_name, v.visit_status
FROM individuals AS i
JOIN visits AS v ON v.individual_id = i.individual_id
LIMIT 20;
```

Existing databases are not modified by upgrading the package; generate a fresh database
for the new schema.
