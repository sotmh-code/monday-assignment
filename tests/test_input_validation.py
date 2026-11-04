import hashlib
from datetime import date

import pytest

from src.io_utils import InputValidationError, format_aum, load_applications
from src.schemas import EXPECTED_COLUMNS
from tests.conftest import SAMPLE_CSV

HEADER = ",".join(EXPECTED_COLUMNS)
GOOD_ROW = 'APP-2026-0901,Test Fund,Institutional,Fixed Income,1000000,02/03/2026,New,"A sufficiently long description of the client."'


def write(tmp_path, text: str):
    p = tmp_path / "in.csv"
    p.write_text(text, encoding="utf-8")
    return p


def test_sample_file_has_15_rows_8_columns_stable_order(sample_apps):
    assert len(sample_apps) == 15
    assert [a.application_id for a in sample_apps] == [f"APP-2026-{n:04d}" for n in range(301, 316)]
    assert SAMPLE_CSV.read_text(encoding="utf-8").splitlines()[0] == HEADER
    assert all(a.is_processable for a in sample_apps)


def test_dates_are_month_day_year_and_source_strings_preserved(sample_apps):
    first = sample_apps[0]
    assert first.submission_date_raw == "01/06/2026"
    assert first.submission_date == date(2026, 1, 6)  # 6 January, not 1 June
    assert first.estimated_aum == 750_000_000
    assert first.estimated_aum_raw == "750000000"


def test_descriptions_preserved_verbatim(sample_apps):
    apex = next(a for a in sample_apps if a.application_id == "APP-2026-0303")
    assert "nominee directors from a corporate services firm" in apex.description
    assert "—" in apex.description  # em dash kept as-is


def test_loading_does_not_modify_source_file():
    before = hashlib.sha256(SAMPLE_CSV.read_bytes()).hexdigest()
    load_applications(SAMPLE_CSV)
    assert hashlib.sha256(SAMPLE_CSV.read_bytes()).hexdigest() == before


def test_wrong_header_rejected(tmp_path):
    p = write(tmp_path, "application_id,client_name\nAPP-2026-0901,X\n")
    with pytest.raises(InputValidationError, match="header"):
        load_applications(p)


def test_duplicate_ids_rejected(tmp_path):
    p = write(tmp_path, f"{HEADER}\n{GOOD_ROW}\n{GOOD_ROW}\n")
    with pytest.raises(InputValidationError, match="duplicate"):
        load_applications(p)


def test_extra_fields_rejected(tmp_path):
    p = write(tmp_path, f"{HEADER}\n{GOOD_ROW},unexpected\n")
    with pytest.raises(InputValidationError, match="wrong number"):
        load_applications(p)


def test_bad_id_rejected(tmp_path):
    p = write(tmp_path, f"{HEADER}\n{GOOD_ROW.replace('APP-2026-0901', 'APP-XYZ')}\n")
    with pytest.raises(InputValidationError, match="invalid application_id"):
        load_applications(p)


def test_expected_count_enforced(tmp_path):
    p = write(tmp_path, f"{HEADER}\n{GOOD_ROW}\n")
    with pytest.raises(InputValidationError, match="Expected 15"):
        load_applications(p, expected_count=15)


def test_row_level_issues_are_kept_and_flagged_not_dropped(tmp_path):
    rows = [
        GOOD_ROW,
        "APP-2026-0902,Blank Desc,Corporate,Fixed Income,5000000,02/03/2026,New,",
        'APP-2026-0903,Bad Numbers,Corporate,Fixed Income,lots,2026-02-03,New,"Another sufficiently long description here."',
    ]
    apps = load_applications(write(tmp_path, HEADER + "\n" + "\n".join(rows) + "\n"))
    assert [a.application_id for a in apps] == ["APP-2026-0901", "APP-2026-0902", "APP-2026-0903"]
    assert apps[0].is_processable
    assert "description is blank" in apps[1].input_issues[0]
    assert any("estimated_aum" in i for i in apps[2].input_issues)
    assert any("MM/DD/YYYY" in i for i in apps[2].input_issues)


def test_format_aum():
    assert format_aum(750_000_000) == "$750M"
    assert format_aum(1_200_000_000) == "$1.2B"
    assert format_aum(2_000_000_000) == "$2B"
    assert format_aum(9_500_000) == "$9.5M"
    assert format_aum(None) == "unknown"
