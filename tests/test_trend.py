from app.transform import CleanCase
from app.trend import build_monthly_event_counts, detect_event_trends, to_month_bucket


def _case(report_id: str, report_date: str, event: str, serious: bool = False) -> CleanCase:
    return CleanCase(
        safetyreportid=report_id,
        report_date=report_date,
        drug="Ibuprofen",
        reactions=[event],
        country="US",
        serious=serious,
        raw={},
        patient_age=None,
        patient_sex=None,
    )


def test_to_month_bucket_parses_iso_date() -> None:
    assert to_month_bucket("2024-03-15") == "2024-03"
    assert to_month_bucket("bad-date") is None


def test_build_monthly_event_counts_fills_month_gaps() -> None:
    cases = [
        _case("r1", "2024-01-10", "NAUSEA"),
        _case("r2", "2024-03-11", "NAUSEA"),
    ]

    counts = build_monthly_event_counts(cases)

    assert counts["NAUSEA"] == {
        "2024-01": 1,
        "2024-02": 0,
        "2024-03": 1,
    }


def test_detect_event_trends_marks_emerging_on_spike() -> None:
    monthly = {
        "RENAL FAILURE ACUTE": {
            "2024-01": 1,
            "2024-02": 1,
            "2024-03": 3,
        }
    }

    trends = detect_event_trends(monthly)
    trend = trends["RENAL FAILURE ACUTE"]

    assert trend.latest_month == "2024-03"
    assert trend.latest_count == 3
    assert trend.emerging is True
    assert trend.growth_ratio >= 1.0
