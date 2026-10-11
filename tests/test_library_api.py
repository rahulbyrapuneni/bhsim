import sqlite3
from bhsim import BHSimulator

def test_library_api_and_question_labels(tmp_path):
    sim = BHSimulator(clients=75, employees=20, seed=42)
    sim.generate(tmp_path / "sample.db")
    assert sim.validate()["valid"]
    assert sim.to_sqlite().exists()
    assert sim.to_csv(tmp_path / "csv")
    with sqlite3.connect(sim.to_sqlite()) as c:
        assert {x[0] for x in c.execute("SELECT instrument_code FROM assessment_instruments")} == {"PHQ9", "GAD7"}
        assert c.execute("SELECT count(*) FROM assessment_responses_readable").fetchone()[0] > 0
        assert c.execute("SELECT count(*) FROM assessment_scores WHERE total_score < 0").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM assessment_responses r JOIN answer_options o ON r.option_id=o.option_id WHERE r.response_value != o.score_value").fetchone()[0] == 0
