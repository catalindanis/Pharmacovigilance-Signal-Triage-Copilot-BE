from __future__ import annotations

from datetime import date

from app.transform import CleanCase


class _FakeBaseline:
    def __init__(self) -> None:
        self.total_reports = 999
        self.event_counts = {"HAEMATEMESIS": 12}


class _FakeMetric:
    def __init__(self) -> None:
        self.event = "HAEMATEMESIS"
        self.n_drug_event = 4
        self.n_drug_total = 4
        self.n_all_event = 12
        self.n_all_total = 999
        self.prr = 246.3692
        self.ror = 355.4829
        self.chi_square_yates = 748.4573
        self.serious_ratio = 0.75
        self.frequency_ratio = 1.0
        self.score = 0.85
        self.valid_signal = True


class _FakeTrend:
    def __init__(self) -> None:
        self.latest_month = "2024-03"
        self.latest_count = 3
        self.baseline_average = 1.0
        self.growth_ratio = 3.0
        self.emerging = True


def test_run_live_prints_signal_packets(monkeypatch, capsys) -> None:
    from app import runner

    cases = [
        CleanCase(
            safetyreportid="id-1",
            report_date="2024-03-15",
            drug="Ibuprofen",
            reactions=["HAEMATEMESIS"],
            country="US",
            serious=True,
            raw={},
            patient_age="54",
            patient_sex="1",
        )
    ]

    monkeypatch.setattr(runner, "fetch_cases_from_db", lambda *args, **kwargs: cases)
    monkeypatch.setattr(runner, "fetch_global_baseline", lambda *args, **kwargs: _FakeBaseline())
    monkeypatch.setattr(runner, "build_signal_metrics", lambda *args, **kwargs: [_FakeMetric()])
    monkeypatch.setattr(runner, "build_monthly_event_counts", lambda *_args, **_kwargs: {"HAEMATEMESIS": {"2024-03": 3}})
    monkeypatch.setattr(runner, "detect_event_trends", lambda *_args, **_kwargs: {"HAEMATEMESIS": _FakeTrend()})
    monkeypatch.setattr(
        runner,
        "generate_signal_packets",
        lambda payload, api_key=None: [type("Packet", (), {"event": "HAEMATEMESIS", "markdown": "# Packet"})()],
    )

    runner.run_live(
        drug_name="ibuprofen",
        start=date(2024, 1, 1),
        end=date(2024, 3, 31),
        limit=10,
        max_pages=None,
        stage2=True,
        use_local_db=True,
        explain_signals=True,
    )

    output = capsys.readouterr().out
    assert "# Signal Evidence Packets" in output
    assert "## 1. HAEMATEMESIS" in output
    assert "# Packet" in output