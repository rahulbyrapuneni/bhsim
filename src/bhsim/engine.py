"""Deterministic synthetic behavioral-health data generation; no PHI inputs."""
from __future__ import annotations

import csv
from contextlib import closing as sqlite_closing
import hashlib
import json
import random
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Config:
    clients: int = 1000
    employees: int = 80
    months: int = 12
    future_days: int = 30
    reference_date: str = "2026-10-10"
    seed: int = 42

    def check(self):
        if min(self.clients, self.employees, self.months) < 1 or self.future_days < 0:
            raise ValueError("clients, employees and months must be positive; future_days cannot be negative")
        date.fromisoformat(self.reference_date)


PROGRAMS = [
    (1, "MH-OP", "Mental Health Outpatient", "MH", .18),
    (2, "MH-CS", "Mental Health Case Management", "MH", .13),
    (3, "MH-CR", "Crisis Services", "MH", .06),
    (4, "SA-OP", "Substance Use Outpatient", "SA", .24),
    (5, "SA-IOP", "Intensive Outpatient", "SA", .21),
    (6, "SA-RC", "Recovery Support", "SA", .16),
    (7, "IDD-CS", "IDD Community Support", "IDD", .11),
    (8, "IDD-CC", "IDD Care Coordination", "IDD", .09),
]
VISIT_TYPES = [(1,"Individual Therapy",60,20),(2,"Case Management",45,17),(3,"Medication Management",30,12),(4,"Crisis Intervention",90,35),(5,"Group Therapy",60,16),(6,"Assessment",45,15)]
# ---IDENTIFIER FORMATS---
ID_LENGTHS = {'individual': 7, 'program': 4, 'enrollment': 9, 'employee': 6, 'assignment': 9, 'supervision': 9, 'location': 5, 'visit': 10, 'visit_type': 5, 'rule': 7, 'productivity': 10, 'instrument': 5, 'question': 7, 'assessment': 10, 'response': 12, 'score': 10, 'option': 6}


def make_id(kind: str, number: int, seed: int = 42) -> str:
    """Seeded, collision-free numeric permutation within each ID's fixed width.

    Different entity kinds have independent namespaces. Unlike zero-padding a
    counter, neighboring source numbers produce unrelated-looking identifiers.
    IDs are stable for the same seed and source number, not cryptographic secrets.
    """
    length = ID_LENGTHS[kind]
    if number < 1 or number >= 10 ** length:
        raise ValueError(f"{kind} ID {number} exceeds the {length}-character capacity")
    right_digits = length // 2
    left_base = 10 ** (length - right_digits)
    right_base = 10 ** right_digits
    left, right = divmod(number, right_base)
    key = f"BHSim|{seed}|{kind}|".encode("ascii")
    # Alternating modular additions are a bijection: distinct inputs cannot
    # generate the same output for a given identifier kind and seed.
    for round_number in range(4):
        digest = hashlib.blake2b(key + bytes([round_number]) + str(right).encode("ascii"), digest_size=8).digest()
        left = (left + int.from_bytes(digest, "big")) % left_base
        digest = hashlib.blake2b(key + bytes([round_number + 4]) + str(left).encode("ascii"), digest_size=8).digest()
        right = (right + int.from_bytes(digest, "big")) % right_base
    return f"{left:0{length - right_digits}d}{right:0{right_digits}d}"


FIRST = ["Alex", "Jordan", "Taylor", "Casey", "Avery", "Morgan", "Sam", "Riley", "Quinn", "Cameron"]
LAST = ["Carter", "Reed", "Morgan", "Patel", "Lee", "Rivera", "Brooks", "Wright", "Clark", "Diaz"]
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE individuals (individual_id TEXT PRIMARY KEY, synthetic_name TEXT NOT NULL, date_of_birth TEXT NOT NULL, sex TEXT NOT NULL);
CREATE TABLE programs (program_id TEXT PRIMARY KEY, program_code TEXT UNIQUE NOT NULL, description TEXT NOT NULL, program_group TEXT NOT NULL, no_show_probability REAL NOT NULL);
CREATE TABLE employees (employee_id TEXT PRIMARY KEY, synthetic_name TEXT NOT NULL, supervisor_id TEXT REFERENCES employees(employee_id));
CREATE TABLE visit_types (visit_type_id TEXT PRIMARY KEY, description TEXT NOT NULL, typical_minutes INTEGER NOT NULL, variation_minutes INTEGER NOT NULL);
CREATE TABLE locations (location_id TEXT PRIMARY KEY, location_name TEXT NOT NULL);
CREATE TABLE individual_programs (enrollment_id TEXT PRIMARY KEY, individual_id TEXT NOT NULL REFERENCES individuals(individual_id), program_id TEXT NOT NULL REFERENCES programs(program_id), start_date TEXT NOT NULL, end_date TEXT, CHECK(end_date IS NULL OR end_date >= start_date));
CREATE TABLE employee_programs (assignment_id TEXT PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id), program_id TEXT NOT NULL REFERENCES programs(program_id), start_date TEXT NOT NULL, end_date TEXT);
CREATE TABLE productivity_rules (rule_id TEXT PRIMARY KEY, program_id TEXT UNIQUE NOT NULL REFERENCES programs(program_id), interval_minutes INTEGER NOT NULL CHECK(interval_minutes>0), rule_version TEXT NOT NULL);
CREATE TABLE visits (visit_id TEXT PRIMARY KEY, individual_id TEXT NOT NULL REFERENCES individuals(individual_id), program_id TEXT NOT NULL REFERENCES programs(program_id), employee_id TEXT NOT NULL REFERENCES employees(employee_id), visit_type_id TEXT NOT NULL REFERENCES visit_types(visit_type_id), location_id TEXT NOT NULL REFERENCES locations(location_id), visit_status TEXT NOT NULL CHECK(visit_status IN ('COMPLETED','NO_SHOW','CANCELED','RESCHEDULED','SCHEDULED')), scheduled_start TEXT NOT NULL, scheduled_duration_minutes INTEGER NOT NULL, actual_start TEXT, actual_end TEXT, actual_duration_minutes INTEGER, documented_at TEXT, rescheduled_to_visit_id TEXT REFERENCES visits(visit_id), productivity_units INTEGER NOT NULL DEFAULT 0);
CREATE TABLE assessment_instruments (instrument_id TEXT PRIMARY KEY, instrument_code TEXT UNIQUE NOT NULL, instrument_version TEXT NOT NULL, item_count INTEGER NOT NULL, scoring_method TEXT NOT NULL);
CREATE TABLE assessments (assessment_id TEXT PRIMARY KEY, individual_id TEXT NOT NULL REFERENCES individuals(individual_id), program_id TEXT REFERENCES programs(program_id), visit_id TEXT REFERENCES visits(visit_id), instrument_id TEXT NOT NULL REFERENCES assessment_instruments(instrument_id), assessed_at TEXT NOT NULL, status TEXT NOT NULL, revision_number INTEGER NOT NULL DEFAULT 1);
CREATE TABLE assessment_responses (response_id TEXT PRIMARY KEY, question_id TEXT NOT NULL REFERENCES assessment_questions(question_id), assessment_id TEXT NOT NULL REFERENCES assessments(assessment_id), item_number INTEGER NOT NULL, option_id TEXT NOT NULL REFERENCES answer_options(option_id), response_value INTEGER NOT NULL CHECK(response_value BETWEEN 0 AND 3), UNIQUE (assessment_id,item_number));
CREATE TABLE assessment_scores (score_id TEXT PRIMARY KEY, assessment_id TEXT UNIQUE NOT NULL REFERENCES assessments(assessment_id), total_score INTEGER NOT NULL, scoring_version TEXT NOT NULL);
CREATE TABLE assessment_questions (question_id TEXT PRIMARY KEY, instrument_id TEXT NOT NULL REFERENCES assessment_instruments(instrument_id), item_number INTEGER NOT NULL, question_text TEXT NOT NULL, UNIQUE(instrument_id,item_number));
CREATE TABLE answer_options (option_id TEXT PRIMARY KEY, instrument_id TEXT NOT NULL REFERENCES assessment_instruments(instrument_id), option_text TEXT NOT NULL, score_value INTEGER NOT NULL CHECK(score_value BETWEEN 0 AND 3), UNIQUE(instrument_id,score_value));
CREATE VIEW assessment_responses_readable AS SELECT a.assessment_id, a.individual_id, i.instrument_code, a.assessed_at, q.item_number, q.question_text, o.option_text AS selected_answer, o.score_value FROM assessment_responses r JOIN assessments a ON a.assessment_id=r.assessment_id JOIN assessment_instruments i ON i.instrument_id=a.instrument_id JOIN assessment_questions q ON q.question_id=r.question_id JOIN answer_options o ON o.option_id=r.option_id;
CREATE TABLE employee_supervision (supervision_id TEXT PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id), supervisor_id TEXT NOT NULL REFERENCES employees(employee_id), start_date TEXT NOT NULL, end_date TEXT, CHECK(employee_id != supervisor_id));
CREATE TABLE visit_productivity (productivity_id TEXT PRIMARY KEY, visit_id TEXT UNIQUE NOT NULL REFERENCES visits(visit_id), rule_id TEXT REFERENCES productivity_rules(rule_id), productivity_units INTEGER NOT NULL);
CREATE TABLE simulation_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX idx_visits_individual_date ON visits(individual_id,scheduled_start);
CREATE INDEX idx_visits_program_date ON visits(program_id,scheduled_start);
CREATE INDEX idx_assessments_individual_date ON assessments(individual_id,assessed_at);
"""


ID_COLUMNS = {'individuals': ['individual_id'], 'programs': ['program_id'], 'employees': ['employee_id', 'supervisor_id'], 'locations': ['location_id'], 'visit_types': ['visit_type_id'], 'individual_programs': ['enrollment_id', 'individual_id', 'program_id'], 'employee_programs': ['assignment_id', 'employee_id', 'program_id'], 'employee_supervision': ['supervision_id', 'employee_id', 'supervisor_id'], 'productivity_rules': ['rule_id', 'program_id'], 'visits': ['visit_id', 'individual_id', 'program_id', 'employee_id', 'visit_type_id', 'location_id', 'rescheduled_to_visit_id'], 'visit_productivity': ['productivity_id', 'visit_id', 'rule_id'], 'assessment_instruments': ['instrument_id'], 'assessment_questions': ['question_id', 'instrument_id'], 'assessments': ['assessment_id', 'individual_id', 'program_id', 'visit_id', 'instrument_id'], 'assessment_responses': ['response_id', 'question_id', 'assessment_id', 'option_id'], 'answer_options': ['option_id', 'instrument_id'], 'assessment_scores': ['score_id', 'assessment_id']}
ID_KINDS = {'individual_id': 'individual', 'program_id': 'program', 'employee_id': 'employee', 'supervisor_id': 'employee', 'location_id': 'location', 'visit_type_id': 'visit_type', 'enrollment_id': 'enrollment', 'assignment_id': 'assignment', 'supervision_id': 'supervision', 'rule_id': 'rule', 'visit_id': 'visit', 'rescheduled_to_visit_id': 'visit', 'productivity_id': 'productivity', 'instrument_id': 'instrument', 'question_id': 'question', 'assessment_id': 'assessment', 'response_id': 'response', 'score_id': 'score', 'option_id': 'option'}

def _pick_datetime(rng: random.Random, earliest: date, latest: date) -> datetime:
    day = earliest + timedelta(days=rng.randint(0, max((latest-earliest).days, 0)))
    return datetime(day.year,day.month,day.day,rng.randint(8,17),rng.choice([0,15,30,45]))



# ---PROGRAM OPERATING HOURS---
# Weekday: Monday=0, Sunday=6. Hours are local wall-clock hours.
PROGRAM_HOURS = {
    1: (set(range(5)), 8, 18),
    2: (set(range(5)), 8, 18),
    3: (set(range(7)), 0, 24),  # Crisis: 24/7
    4: (set(range(6)), 8, 19),
    5: (set(range(6)), 8, 19),
    6: (set(range(6)), 8, 19),
    7: (set(range(5)), 8, 17),
    8: (set(range(5)), 8, 17),
}


def _program_slot(rng, program_number, earliest, latest, duration, after=None):
    """Sample a valid slot (end-exclusive) inside program operating hours."""
    days, opening, closing = PROGRAM_HOURS[program_number]
    start_day = max(earliest, after.date() if after else earliest)
    eligible = []
    day = start_day
    while day <= latest:
        if day.weekday() in days:
            base = datetime.combine(day, datetime.min.time())
            minimum = base + timedelta(hours=opening)
            maximum = base + timedelta(hours=closing, minutes=-duration)
            if after is not None:
                minimum = max(minimum, after + timedelta(minutes=15))
            # Quarter-hour start times. Ceiling to next quarter.
            minimum += timedelta(minutes=(-minimum.minute) % 15, seconds=-minimum.second, microseconds=-minimum.microsecond)
            if minimum <= maximum:
                eligible.append((minimum, maximum))
        day += timedelta(days=1)
    if not eligible:
        raise ValueError(f"No operating slot for program {program_number} between {start_day} and {latest}")
    first, last = rng.choice(eligible)
    return first + timedelta(minutes=15 * rng.randrange(int((last-first).total_seconds()//900)+1))


def _visit_within_hours(visit, program_index):
    days, opening, closing = PROGRAM_HOURS[program_index[visit[2]]]
    start = datetime.fromisoformat(visit[9] or visit[7])
    length = (datetime.fromisoformat(visit[10])-start).total_seconds()/60 if visit[10] else visit[8]
    end = start + timedelta(minutes=length)
    return (start.weekday() in days and start.date()==end.date()
            and start.hour*60+start.minute >= opening*60
            and end.hour*60+end.minute <= closing*60)


def _resolve_completed_staff_overlaps(visits, by_program, program_index):
    """Prefer an assigned, available employee for overlapping completed visits."""
    from collections import defaultdict
    busy = defaultdict(list)
    for visit in sorted((v for v in visits if v[6] == "COMPLETED"), key=lambda v: (v[9], v[0])):
        begin = datetime.fromisoformat(visit[9])
        end = datetime.fromisoformat(visit[10])
        eligible = by_program[program_index[visit[2]]]
        alternatives = [visit[3]] + [emp for emp in eligible if emp != visit[3]]
        for employee in alternatives:
            if all(end <= left or begin >= right for left, right in busy[employee]):
                visit[3] = employee
                busy[employee].append((begin, end))
                break
        else:
            # No available colleague: adjust only this encounter to a free slot
            # after its planned time. Do not alter visit date or client identity.
            days, opening, closing = PROGRAM_HOURS[program_index[visit[2]]]
            base = datetime.combine(begin.date(), datetime.min.time())
            service_minutes = int((end - begin).total_seconds() / 60)
            earliest = base + timedelta(hours=opening)
            latest = base + timedelta(hours=closing, minutes=-service_minutes)
            possible = []
            trial = earliest
            while trial <= latest:
                possible.append(trial)
                trial += timedelta(minutes=15)
            for trial in sorted(possible, key=lambda x: abs((x-begin).total_seconds())):
                finish = trial + (end-begin)
                if all(finish <= left or trial >= right for left,right in busy[visit[3]]):
                    delta = trial-begin
                    visit[7] = max(earliest, datetime.fromisoformat(visit[7])+delta).isoformat(timespec="minutes")
                    visit[9] = trial.isoformat(timespec="minutes")
                    visit[10] = finish.isoformat(timespec="minutes")
                    visit[12] = (datetime.fromisoformat(visit[12])+delta).isoformat(timespec="minutes")
                    busy[visit[3]].append((trial,finish))
                    break
            else:
                raise ValueError("Insufficient same-day staff capacity for completed visits")



def generate(path: str | Path, config: Config | None = None) -> dict:
    """Generate a new SQLite database. Existing destinations are refused."""
    config = config or Config()
    config.check()
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(config.seed)
    make_id = lambda kind, number: globals()["make_id"](kind, number, config.seed)
    program_index = {make_id("program", row[0]): row[0] for row in PROGRAMS}
    today = date.fromisoformat(config.reference_date)
    start = today - timedelta(days=round(config.months * 30.44))
    counts = {}
    try:
        with sqlite_closing(sqlite3.connect(target)) as con, con:
            con.executescript(SCHEMA)
            con.executemany("INSERT INTO programs VALUES (?,?,?,?,?)",[(make_id("program",p[0]),*p[1:]) for p in PROGRAMS])
            con.executemany("INSERT INTO visit_types VALUES (?,?,?,?)", [(make_id("visit_type",v[0]),*v[1:]) for v in VISIT_TYPES])
            con.executemany("INSERT INTO locations VALUES (?,?)", [(make_id("location",i),name) for i,name in [(1,"North Center"),(2,"South Center"),(3,"Telehealth")]])
            con.executemany("INSERT INTO productivity_rules VALUES (?,?,?,?)",[(make_id("rule",p[0]),make_id("program",p[0]),15,"demo-v1") for p in PROGRAMS])
            individuals=[]
            for i in range(1, config.clients+1):
                dob = today - timedelta(days=rng.randint(16*365,80*365))
                individuals.append((make_id("individual",i), f"{rng.choice(FIRST)} {rng.choice(LAST)} #{i}",dob.isoformat(),rng.choice(["F","M","X"])))
            con.executemany("INSERT INTO individuals VALUES (?,?,?,?)",individuals)
            employees=[]
            for i in range(1,config.employees+1):
                employees.append((make_id("employee",i),f"{rng.choice(FIRST)} {rng.choice(LAST)} Staff #{i}",make_id("employee",rng.randint(1,i-1)) if i>1 and rng.random()<.8 else None))
            con.executemany("INSERT INTO employees VALUES (?,?,?)",employees)
            employee_assignments=[]
            by_program={p[0]:[] for p in PROGRAMS}
            for e in range(1,config.employees+1):
                selected=rng.sample([p[0] for p in PROGRAMS],k=rng.randint(1, min(3,len(PROGRAMS))))
                for p in selected:
                    employee_assignments.append((make_id("assignment",len(employee_assignments)+1),make_id("employee",e),make_id("program",p),start.isoformat(),None))
                    by_program[p].append(make_id("employee",e))
            # Guarantee that each program has at least one assigned worker.
            for p,staff in by_program.items():
                if not staff:
                    employee_assignments.append((make_id("assignment",len(employee_assignments)+1),make_id("employee",1),make_id("program",p),start.isoformat(),None))
                    by_program[p].append(make_id("employee",1))
            con.executemany("INSERT INTO employee_programs VALUES (?,?,?,?,?)",employee_assignments)
            supervisors=[]
            for e,_,supervisor in employees:
                if supervisor:
                    supervisors.append((make_id("supervision",len(supervisors)+1),e,supervisor,start.isoformat(),None))
            con.executemany("INSERT INTO employee_supervision VALUES (?,?,?,?,?)",supervisors)
            # ---CLIENT ENROLLMENT LIFECYCLES---
            enrollments = []
            client_programs = {}
            enrollment_episodes = {}
            history_days = (today - start).days
            for i in range(1, config.clients + 1):
                chosen = rng.sample([p[0] for p in PROGRAMS if p[0] != 3], k=rng.randint(1, 3))
                client_programs[i] = [make_id("program", p) for p in chosen]
                enrollment_episodes[i] = []
                for program_number in chosen:
                    program_id = make_id("program", program_number)
                    # Leave at least four weeks of potential encounter history.
                    admission = start + timedelta(days=rng.randint(0, max(0, history_days - 35)))
                    remaining = (today - admission).days
                    discharge = None
                    if remaining >= 100 and rng.random() < 0.55:
                        discharge = admission + timedelta(days=rng.randint(42, remaining - 30))
                    episodes = [(admission, discharge)]
                    if discharge is not None and (today - discharge).days >= 50 and rng.random() < 0.40:
                        gap = rng.randint(15, (today - discharge).days - 25)
                        episodes.append((discharge + timedelta(days=gap), None))
                    for episode_start, episode_end in episodes:
                        enrollments.append((
                            make_id("enrollment", len(enrollments) + 1),
                            make_id("individual", i), program_id,
                            episode_start.isoformat(),
                            episode_end.isoformat() if episode_end else None,
                        ))
                        enrollment_episodes[i].append((program_id, episode_start, episode_end))
            con.executemany("INSERT INTO individual_programs VALUES (?,?,?,?,?)", enrollments)
            visits=[]
            completed_by_client={}
            visit_id=0
            visit_episode_end = {}
            for i in range(1,config.clients+1):
                for _ in range(rng.randint(3, min(25,max(4,config.months*2)))):
                    # ---SCHEDULE WITHIN ONE VALID ENROLLMENT EPISODE---
                    eligible = [
                        episode for episode in enrollment_episodes[i]
                        if (min(episode[2] or today, today) - episode[1]).days >= 21
                    ]
                    if not eligible:
                        continue
                    p, episode_start, episode_end = rng.choice(eligible)
                    vt = rng.choice(VISIT_TYPES)
                    last_day = min(episode_end or today, today)
                    # Historical visits are at least 14 days before the episode ends
                    # so that replacements can occur within the same enrollment.
                    duration_buffer = max(vt[2] + 90, 180)
                    scheduled = _program_slot(
                        rng, program_index[p], episode_start,
                        last_day - timedelta(days=14), duration_buffer,
                    )
                    r=rng.random()
                    probability=PROGRAMS[program_index[p]-1][4]
                    status="NO_SHOW" if r<probability else "CANCELED" if r<probability+.08 else "RESCHEDULED" if r<probability+.11 else "COMPLETED"
                    duration=max(10,round(rng.gauss(vt[2],vt[3])))
                    if status == "COMPLETED":
                        actual_start = scheduled + timedelta(minutes=rng.randint(-5, 12))
                        _, opening, closing = PROGRAM_HOURS[program_index[p]]
                        open_time = datetime.combine(scheduled.date(), datetime.min.time()) + timedelta(hours=opening)
                        close_time = datetime.combine(scheduled.date(), datetime.min.time()) + timedelta(hours=closing)
                        actual_start = max(open_time, actual_start)
                        duration = min(duration, int((close_time - actual_start).total_seconds() // 60))
                    else:
                        actual_start = None
                    actual_end=actual_start+timedelta(minutes=duration) if actual_start else None
                    visit_id+=1
                    visits.append([make_id("visit",visit_id),make_id("individual",i),p,rng.choice(by_program[program_index[p]]),make_id("visit_type",vt[0]),make_id("location",rng.randint(1,3)),status,scheduled.isoformat(timespec="minutes"),vt[2],actual_start.isoformat(timespec="minutes") if actual_start else None,actual_end.isoformat(timespec="minutes") if actual_end else None,duration if actual_start else None,(actual_end+timedelta(days=rng.randint(0,3))).isoformat(timespec="minutes") if actual_end else None,None,(duration+7)//15 if actual_start else 0])
                    visit_episode_end[visits[-1][0]] = episode_end
                    if status=="COMPLETED":
                        completed_by_client.setdefault(i,[]).append(visits[-1])
                for _ in range(rng.randint(0,max(1,config.future_days//20))):
                    active = [p for p, admission, discharge in enrollment_episodes[i]
                              if admission <= today and discharge is None]
                    if not active:
                        continue
                    p = rng.choice(active)
                    vt = rng.choice(VISIT_TYPES)
                    sched=_program_slot(rng,program_index[p],today+timedelta(days=1),today+timedelta(days=max(1,config.future_days)),vt[2]) if config.future_days else None
                    if sched is None: continue
                    visit_id+=1
                    visits.append([make_id("visit",visit_id),make_id("individual",i),p,rng.choice(by_program[program_index[p]]),make_id("visit_type",vt[0]),make_id("location",rng.randint(1,3)),"SCHEDULED",sched.isoformat(timespec="minutes"),vt[2],None,None,None,None,None,0])
            # ---RESCHEDULED APPOINTMENTS---
            original_rescheduled = [v for v in visits if v[6] == "RESCHEDULED"]
            for original in original_rescheduled:
                original_date = datetime.fromisoformat(original[7])
                visit_duration = next(vt[2] for vt in VISIT_TYPES if make_id("visit_type", vt[0]) == original[4])
                sched = _program_slot(
                    rng, program_index[original[2]],
                    original_date.date() + timedelta(days=1),
                    min(original_date.date() + timedelta(days=14), visit_episode_end[original[0]] or (today + timedelta(days=14))),
                    max(visit_duration + 90, 180),
                    after=original_date,
                )
                visit_id += 1
                if sched.date() > today:
                    status = "SCHEDULED"
                else:
                    probability = PROGRAMS[program_index[original[2]] - 1][4]
                    outcome = rng.random()
                    status = (
                        "NO_SHOW" if outcome < probability
                        else "CANCELED" if outcome < probability + 0.08
                        else "COMPLETED"
                    )
                actual_start = None
                actual_end = None
                actual_duration = None
                documented_at = None
                units = 0
                if status == "COMPLETED":
                    visit_type_number = next(
                        vt for vt in VISIT_TYPES
                        if make_id("visit_type", vt[0]) == original[4]
                    )
                    actual_duration = max(10, round(rng.gauss(visit_type_number[2], visit_type_number[3])))
                    actual_start = sched + timedelta(minutes=rng.randint(-5, 12))
                    _, opening, closing = PROGRAM_HOURS[program_index[original[2]]]
                    open_time = datetime.combine(sched.date(), datetime.min.time()) + timedelta(hours=opening)
                    close_time = datetime.combine(sched.date(), datetime.min.time()) + timedelta(hours=closing)
                    actual_start = max(open_time, actual_start)
                    actual_duration = min(actual_duration, int((close_time - actual_start).total_seconds() // 60))
                    actual_end = actual_start + timedelta(minutes=actual_duration)
                    documented_at = actual_end + timedelta(days=rng.randint(0, 3))
                    units = (actual_duration + 7) // 15
                replacement = [
                    make_id("visit", visit_id), original[1], original[2],
                    original[3], original[4], original[5], status,
                    sched.isoformat(timespec="minutes"), original[8],
                    actual_start.isoformat(timespec="minutes") if actual_start else None,
                    actual_end.isoformat(timespec="minutes") if actual_end else None,
                    actual_duration,
                    documented_at.isoformat(timespec="minutes") if documented_at else None,
                    None, units,
                ]
                original[13] = replacement[0]
                visits.append(replacement)
            _resolve_completed_staff_overlaps(visits, by_program, program_index)
            # Insert all rows before assigning self-referential reschedule links.
            links=[(v[13],v[0]) for v in visits if v[13] is not None]
            for v in visits:
                v[13]=None
            con.executemany("INSERT INTO visits VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",visits)
            con.executemany("UPDATE visits SET rescheduled_to_visit_id=? WHERE visit_id=?",links)
            # ---ASSESSMENT INSTRUMENT CATALOG---
            instruments = [(1, "PHQ9", "v1", 9, "SUM_COMPLETE_ITEMS"),
                           (2, "GAD7", "v1", 7, "SUM_COMPLETE_ITEMS")]
            con.executemany("INSERT INTO assessment_instruments VALUES (?,?,?,?,?)",
                [(make_id("instrument", n), code, version, count, method)
                 for n, code, version, count, method in instruments])

            phq9 = [
                "Little interest or pleasure in doing things",
                "Feeling down, depressed, or hopeless",
                "Trouble falling or staying asleep, or sleeping too much",
                "Feeling tired or having little energy",
                "Poor appetite or overeating",
                "Feeling bad about yourself, or that you are a failure or have let yourself or your family down",
                "Trouble concentrating on things, such as reading the newspaper or watching television",
                "Moving or speaking so slowly that other people could have noticed, or the opposite—being fidgety or restless",
                "Thoughts that you would be better off dead or of hurting yourself in some way",
            ]
            gad7 = [
                "Feeling nervous, anxious, or on edge",
                "Not being able to stop or control worrying",
                "Worrying too much about different things",
                "Trouble relaxing",
                "Being so restless that it is hard to sit still",
                "Becoming easily annoyed or irritable",
                "Feeling afraid as if something awful might happen",
            ]
            option_texts = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
            question_lookup, option_lookup = {}, {}
            question_rows, option_rows = [], []
            for n, texts in [(1, phq9), (2, gad7)]:
                for item, prompt in enumerate(texts, 1):
                    qid = make_id("question", len(question_rows) + 1)
                    question_rows.append((qid, make_id("instrument", n), item, prompt))
                    question_lookup[(n, item)] = qid
                for score, text in enumerate(option_texts):
                    oid = make_id("option", len(option_rows) + 1)
                    option_rows.append((oid, make_id("instrument", n), text, score))
                    option_lookup[(n, score)] = oid
            con.executemany("INSERT INTO assessment_questions VALUES (?,?,?,?)", question_rows)
            con.executemany("INSERT INTO answer_options VALUES (?,?,?,?)", option_rows)

            # ---LONGITUDINAL SYNTHETIC SCREENING---
            assessments, responses, scores = [], [], []
            assessment_id = response_id = score_id = 0
            for i in range(1, config.clients + 1):
                client_visits = sorted(completed_by_client.get(i, []), key=lambda v: v[9])
                if not client_visits:
                    continue
                for n, item_count in [(1, 9), (2, 7)]:
                    if n == 2 and rng.random() < 0.25:
                        continue
                    severity = rng.randint(3, item_count * 3 - 3)
                    direction = rng.choice([-1, -1, 0, 0, 1])
                    target_count = min(len(client_visits), rng.randint(1, 4))
                    positions = sorted(rng.sample(range(len(client_visits)), target_count))
                    for order, position in enumerate(positions):
                        v = client_visits[position]
                        assessment_id += 1
                        aid = make_id("assessment", assessment_id)
                        level = max(0, min(item_count * 3, severity + 2 * direction * order + rng.randint(-3, 3)))
                        values = [0] * item_count
                        for _ in range(level):
                            available = [j for j, val in enumerate(values) if val < 3]
                            values[rng.choice(available)] += 1
                        complete = rng.random() >= 0.08
                        answered = item_count if complete else rng.randint(1, item_count - 1)
                        actual_begin = datetime.fromisoformat(v[9])
                        actual_end = datetime.fromisoformat(v[10])
                        assessed_at = actual_begin + (actual_end - actual_begin) / 2
                        linked_visit = v[0] if rng.random() < 0.85 else None
                        assessments.append((aid, make_id("individual", i), v[2], linked_visit,
                             make_id("instrument", n), assessed_at.isoformat(timespec="minutes"),
                             "COMPLETE" if complete else "INCOMPLETE", 1))
                        for item, value in enumerate(values[:answered], 1):
                            response_id += 1
                            responses.append((make_id("response", response_id),
                                question_lookup[(n, item)], aid, item, option_lookup[(n, value)], value))
                        if complete:
                            score_id += 1
                            scores.append((make_id("score", score_id), aid, sum(values),
                                           "PHQ9_SUM_V1" if n == 1 else "GAD7_SUM_V1"))
            con.executemany("INSERT INTO assessments VALUES (?,?,?,?,?,?,?,?)", assessments)
            con.executemany("INSERT INTO assessment_responses VALUES (?,?,?,?,?,?)", responses)
            con.executemany("INSERT INTO assessment_scores VALUES (?,?,?,?)", scores)
            con.executemany("INSERT INTO visit_productivity VALUES (?,?,?,?)",[
                (make_id("productivity",n),v[0],make_id("rule",program_index[v[2]]),v[14])
                for n,v in enumerate(visits,1)])
            con.executemany("INSERT INTO simulation_metadata VALUES (?,?)",[("config",json.dumps(asdict(config),sort_keys=True)),("engine_version","1.0.0rc1"),("synthetic_only","true"),("instrument_scope","PHQ-9 and GAD-7; complete-case summation only; synthetic screening data"),("id_lengths",json.dumps(ID_LENGTHS,sort_keys=True)),("id_scheme","seeded-numeric-permutation-v1")])
            counts={t:con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ["individuals","programs","employees","individual_programs","employee_programs","visits","assessments","assessment_responses"]}
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except PermissionError:
            pass  # Preserve the original generator error on Windows.
        raise
    return counts


def validate(path: str | Path) -> dict:
    """Independently check relational and temporal invariants in the output."""
    issues=[]
    with sqlite_closing(sqlite3.connect(path)) as con:
        con.execute("PRAGMA foreign_keys=ON")
        fk=con.execute("PRAGMA foreign_key_check").fetchall()
        if fk: issues.append(f"Foreign key failures: {len(fk)}")
        # Check every primary and foreign ID for fixed-width numeric TEXT storage.
        for table, cols in ID_COLUMNS.items():
            for col in cols:
                kind=ID_KINDS[col]
                n=con.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL AND (typeof({col})!='text' OR length({col})!=? OR {col} GLOB '*[^0-9]*')", (ID_LENGTHS[kind],)).fetchone()[0]
                if n: issues.append(f"invalid_id_format {table}.{col}: {n}")
        checks={
            "incorrect_productivity": "SELECT COUNT(*) FROM visits WHERE productivity_units != CASE WHEN visit_status='COMPLETED' THEN (actual_duration_minutes+7)/15 ELSE 0 END",
            "invalid_actual_data": "SELECT COUNT(*) FROM visits WHERE (visit_status='COMPLETED' AND (actual_start IS NULL OR actual_end IS NULL OR actual_duration_minutes<=0)) OR (visit_status!='COMPLETED' AND (actual_start IS NOT NULL OR actual_end IS NOT NULL OR actual_duration_minutes IS NOT NULL))",
            "invalid_reschedule": "SELECT COUNT(*) FROM visits a LEFT JOIN visits b ON a.rescheduled_to_visit_id=b.visit_id WHERE (a.visit_status='RESCHEDULED' AND (b.visit_id IS NULL OR a.individual_id!=b.individual_id OR a.visit_id=b.visit_id)) OR (a.visit_status!='RESCHEDULED' AND a.rescheduled_to_visit_id IS NOT NULL)",
            "invalid_employee_program": "SELECT COUNT(*) FROM visits v WHERE NOT EXISTS (SELECT 1 FROM employee_programs ep WHERE ep.employee_id=v.employee_id AND ep.program_id=v.program_id AND date(v.scheduled_start) >= ep.start_date AND (ep.end_date IS NULL OR date(v.scheduled_start)<=ep.end_date))",
            "incorrect_assessment_score": "SELECT COUNT(*) FROM assessment_scores s JOIN assessments a ON s.assessment_id=a.assessment_id JOIN assessment_instruments i ON a.instrument_id=i.instrument_id WHERE s.total_score != (SELECT SUM(response_value) FROM assessment_responses r WHERE r.assessment_id=s.assessment_id) OR (SELECT COUNT(*) FROM assessment_responses r WHERE r.assessment_id=s.assessment_id)!=i.item_count OR a.status!='COMPLETE'",
            "assessment_option_mismatch": "SELECT COUNT(*) FROM assessment_responses r JOIN assessments a ON r.assessment_id=a.assessment_id JOIN answer_options o ON o.option_id=r.option_id WHERE a.instrument_id!=o.instrument_id OR o.score_value!=r.response_value",
            "assessment_response_question_mismatch": "SELECT COUNT(*) FROM assessment_responses r JOIN assessments a ON r.assessment_id=a.assessment_id JOIN assessment_questions q ON q.question_id=r.question_id WHERE a.instrument_id!=q.instrument_id OR q.item_number!=r.item_number",
            "invalid_question_count": "SELECT COUNT(*) FROM assessments a JOIN assessment_instruments i ON i.instrument_id=a.instrument_id WHERE (a.status='COMPLETE' AND (SELECT COUNT(*) FROM assessment_responses r WHERE r.assessment_id=a.assessment_id)!=i.item_count) OR (a.status='INCOMPLETE' AND (SELECT COUNT(*) FROM assessment_responses r WHERE r.assessment_id=a.assessment_id)>=i.item_count)",
            "incomplete_assessment_scored": "SELECT COUNT(*) FROM assessments a JOIN assessment_scores s ON a.assessment_id=s.assessment_id WHERE a.status!='COMPLETE'",
            "missing_complete_scores": "SELECT COUNT(*) FROM assessments a LEFT JOIN assessment_scores s ON a.assessment_id=s.assessment_id WHERE a.status='COMPLETE' AND s.score_id IS NULL",
            "assessment_visit_mismatch": "SELECT COUNT(*) FROM assessments a JOIN visits v ON a.visit_id=v.visit_id WHERE a.individual_id!=v.individual_id OR a.program_id!=v.program_id OR v.visit_status!='COMPLETED'",
            "future_completed": "SELECT COUNT(*) FROM visits WHERE visit_status='COMPLETED' AND date(scheduled_start)>(SELECT json_extract(value,'$.reference_date') FROM simulation_metadata WHERE key='config')",
            "visits_outside_enrollment": "SELECT COUNT(*) FROM visits v WHERE NOT EXISTS (SELECT 1 FROM individual_programs ip WHERE ip.individual_id=v.individual_id AND ip.program_id=v.program_id AND date(v.scheduled_start)>=ip.start_date AND (ip.end_date IS NULL OR date(v.scheduled_start)<=ip.end_date))",
            "overlapping_enrollment_episodes": "SELECT COUNT(*) FROM individual_programs a JOIN individual_programs b ON a.individual_id=b.individual_id AND a.program_id=b.program_id AND a.enrollment_id < b.enrollment_id AND a.start_date <= COALESCE(b.end_date,'9999-12-31') AND b.start_date <= COALESCE(a.end_date,'9999-12-31')",
        }
        for name,query in checks.items():
            try:
                n=con.execute(query).fetchone()[0]
                if n: issues.append(f"{name}: {n}")
            except sqlite3.DatabaseError as e:
                issues.append(f"{name}: validation query failed: {e}")
    # ---VALIDATE OPERATING HOURS AND STAFF CONFLICTS---
    with sqlite_closing(sqlite3.connect(path)) as con:
        lookup = {row[1]: row[0] for row in PROGRAMS}
        pmap = {pid: lookup[code] for pid, code in con.execute("SELECT program_id,program_code FROM programs")}
        violations = 0
        for pid, start_text, duration, actual_start, actual_end in con.execute(
            "SELECT program_id,scheduled_start,scheduled_duration_minutes,actual_start,actual_end FROM visits"
        ):
            days, opening, closing = PROGRAM_HOURS[pmap[pid]]
            sched = datetime.fromisoformat(start_text)
            day_start = datetime.combine(sched.date(), datetime.min.time())
            opens = day_start + timedelta(hours=opening)
            closes = day_start + timedelta(hours=closing)
            invalid = sched.weekday() not in days or sched < opens or sched + timedelta(minutes=duration) > closes
            if actual_start and actual_end:
                begin = datetime.fromisoformat(actual_start)
                end = datetime.fromisoformat(actual_end)
                invalid |= begin < opens or end > closes or end <= begin
            violations += bool(invalid)
        if violations:
            issues.append(f"program_operating_hours_violations: {violations}")
        overlaps = con.execute("""SELECT COUNT(*) FROM visits a JOIN visits b
            ON a.employee_id=b.employee_id AND a.visit_id < b.visit_id
            WHERE a.visit_status='COMPLETED' AND b.visit_status='COMPLETED'
              AND a.actual_start < b.actual_end AND b.actual_start < a.actual_end""").fetchone()[0]
        if overlaps:
            issues.append(f"employee_service_overlaps: {overlaps}")
    return {"valid": not issues,"issues":issues}


def export_csv(path: str | Path, directory: str | Path) -> list[str]:
    destination=Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    output=[]
    with sqlite_closing(sqlite3.connect(path)) as con:
        tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for table in tables:
            filepath=destination/(table+".csv")
            cursor=con.execute(f'SELECT * FROM "{table}"')
            with filepath.open("w",newline="",encoding="utf-8") as f:
                writer=csv.writer(f)
                writer.writerow([d[0] for d in cursor.description])
                for chunk in iter(lambda:cursor.fetchmany(10000),[]):
                    writer.writerows(chunk)
            output.append(str(filepath))
    return output
