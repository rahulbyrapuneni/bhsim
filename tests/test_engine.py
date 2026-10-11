import sqlite3
from dataclasses import replace
import pytest
from bhsim import Config, generate, validate, export_csv


def test_generation_and_validation(tmp_path):
    path=tmp_path/'test.db'
    counts=generate(path,Config(clients=30,employees=8,months=4,future_days=25,seed=7))
    assert counts['individuals']==30
    assert counts['visits']>0
    assert counts['assessment_responses'] >= counts['assessments']*3
    assert validate(path)=={'valid':True,'issues':[]}


def test_reproducibility(tmp_path):
    config=Config(clients=20,employees=8,seed=33)
    generate(tmp_path/'a.db',config)
    generate(tmp_path/'b.db',config)
    with sqlite3.connect(tmp_path/'a.db') as a,sqlite3.connect(tmp_path/'b.db') as b:
        for table in ['visits','assessments','assessment_responses']:
            assert a.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()==b.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()


def test_refuses_overwrite(tmp_path):
    path=tmp_path/'test.db'
    generate(path,Config(clients=5,employees=3))
    with pytest.raises(FileExistsError):generate(path,Config(clients=5,employees=3))


def test_invalid_config(tmp_path):
    with pytest.raises(ValueError):generate(tmp_path/'bad.db',Config(clients=0))


def test_validation_detects_corrupt_score(tmp_path):
    path=tmp_path/'test.db'
    generate(path,Config(clients=15,employees=5))
    with sqlite3.connect(path) as con:
        con.execute('UPDATE assessment_scores SET total_score=99 WHERE assessment_id=(SELECT MIN(assessment_id) FROM assessment_scores)')
    assert any('incorrect_assessment_score' in i for i in validate(path)['issues'])


def test_csv_export(tmp_path):
    path=tmp_path/'test.db';generate(path,Config(clients=5,employees=4))
    outputs=export_csv(path,tmp_path/'csv')
    assert len(outputs)>=10
    assert (tmp_path/'csv'/'visits.csv').exists()


def test_all_fixed_width_numeric_ids_and_foreign_keys(tmp_path):
    from bhsim.engine import ID_COLUMNS, ID_LENGTHS, ID_KINDS
    db=tmp_path/'ids.db'
    generate(db,Config(clients=100,employees=20,seed=42))
    with sqlite3.connect(db) as con:
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
        for table,cols in ID_COLUMNS.items():
            for col in cols:
                rows=con.execute(f'SELECT {col} FROM {table} WHERE {col} IS NOT NULL').fetchall()
                assert all(isinstance(value,str) and value.isascii() and value.isdigit() and len(value)==ID_LENGTHS[ID_KINDS[col]] for (value,) in rows),(table,col)
        assert con.execute('SELECT individual_id FROM individuals ORDER BY individual_id LIMIT 1').fetchone()[0]!='0000001'
        assert con.execute('SELECT visit_id FROM visits ORDER BY visit_id LIMIT 1').fetchone()[0]!='0000000001'
        assert con.execute('SELECT COUNT(*) FROM assessment_responses WHERE length(response_id)!=12').fetchone()[0]==0
    assert validate(db)['valid']
    outputs=export_csv(db,tmp_path/'csv')
    with (tmp_path/'csv'/'individuals.csv').open() as f:
        import csv
        row=next(csv.DictReader(f))
        assert len(row['individual_id'])==7 and row['individual_id'].isdigit()


def test_id_capacity_rejected():
    from bhsim.engine import make_id
    assert len(make_id('program',1))==4 and make_id('program',1).isdigit()
    with pytest.raises(ValueError): make_id('program',10000)


def test_seeded_ids_are_unique_nonsequential_and_deterministic():
    from bhsim.engine import make_id, ID_LENGTHS
    for kind, length in ID_LENGTHS.items():
        count=min(200, 10**length-1)
        values=[make_id(kind,i,seed=123) for i in range(1,count+1)]
        assert len(set(values))==count
        assert all(len(v)==length and v.isdigit() for v in values)
        assert values==[make_id(kind,i,seed=123) for i in range(1,count+1)]
        assert values!=[f'{i:0{length}d}' for i in range(1,count+1)]
        assert values!=[make_id(kind,i,seed=124) for i in range(1,count+1)]

def test_seeded_foreign_keys_survive_csv_export(tmp_path):
    db=tmp_path/'random.db'
    generate(db,Config(clients=150,employees=20,seed=234))
    assert validate(db)['valid']
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT COUNT(*) FROM visits v LEFT JOIN individuals i ON v.individual_id=i.individual_id WHERE i.individual_id IS NULL').fetchone()[0]==0
        assert con.execute('SELECT COUNT(DISTINCT visit_id) FROM visits').fetchone()[0]==con.execute('SELECT COUNT(*) FROM visits').fetchone()[0]
    export_csv(db,tmp_path/'csv')
    import csv
    with (tmp_path/'csv'/'visits.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert all(len(r['visit_id'])==10 and r['visit_id'].isdigit() for r in rows)
