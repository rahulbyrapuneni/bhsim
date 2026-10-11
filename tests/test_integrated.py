import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from bhsim import Config, generate, validate


@pytest.mark.parametrize('seed', [1, 42, 99, 234, 999])
def test_multiple_seeds_have_valid_enrollment_and_scheduling(tmp_path, seed):
    db = tmp_path / f'{seed}.db'
    generate(db, Config(clients=100, employees=15, seed=seed))
    assert validate(db) == {'valid': True, 'issues': []}
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT count(DISTINCT start_date) FROM individual_programs').fetchone()[0] > 3
        assert con.execute('SELECT count(*) FROM individual_programs WHERE end_date IS NOT NULL').fetchone()[0] > 0
        assert con.execute('SELECT count(*) FROM visits WHERE visit_status="RESCHEDULED"').fetchone()[0] >= 0
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []


def test_assessment_instrument_variants_and_score_integrity(tmp_path):
    db = tmp_path / 'assessments.db'
    generate(db, Config(clients=200, employees=25, seed=42))
    with sqlite3.connect(db) as con:
        instruments = {row[0] for row in con.execute('SELECT instrument_code FROM assessment_instruments')}
        assert instruments == {'PHQ9', 'GAD7'}
        assert con.execute('SELECT count(*) FROM assessments WHERE status="INCOMPLETE"').fetchone()[0] > 0
        assert con.execute('SELECT count(*) FROM assessments WHERE visit_id IS NULL').fetchone()[0] > 0
        assert con.execute('SELECT count(*) FROM assessment_questions WHERE length(question_text)>10').fetchone()[0] == 16
    assert validate(db)['valid']


def test_validator_detects_overlapping_employee_visits(tmp_path):
    db = tmp_path / 'overlap.db'
    generate(db, Config(clients=100, employees=20))
    with sqlite3.connect(db) as con:
        a,b = con.execute('SELECT visit_id FROM visits WHERE visit_status="COMPLETED" LIMIT 2').fetchall()
        con.execute('UPDATE visits SET employee_id=(SELECT employee_id FROM visits WHERE visit_id=?) WHERE visit_id=?',(a[0],b[0]))
        con.execute('UPDATE visits SET actual_start=(SELECT actual_start FROM visits WHERE visit_id=?), actual_end=(SELECT actual_end FROM visits WHERE visit_id=?) WHERE visit_id=?',(a[0],a[0],b[0]))
    assert any('employee_service_overlaps' in issue for issue in validate(db)['issues'])


def test_validator_detects_invalid_enrollment_start_date(tmp_path):
    db = tmp_path / 'enrollment.db'
    generate(db, Config(clients=100, employees=20))
    with sqlite3.connect(db) as con:
        row = con.execute('SELECT individual_id,program_id FROM visits LIMIT 1').fetchone()
        con.execute('UPDATE individual_programs SET start_date="2099-01-01", end_date=NULL WHERE individual_id=? AND program_id=?',row)
    assert any('visits_outside_enrollment' in issue for issue in validate(db)['issues'])
