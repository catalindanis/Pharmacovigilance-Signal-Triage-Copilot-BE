from datetime import date

import requests

from app.baseline import fetch_global_baseline


class _Client:
    def __init__(self) -> None:
        self.event_queries: list[str] = []

    def fetch_total_reports(self, search: str) -> int:
        if 'reactionmeddrapt.exact:"NAUSEA"' in search:
            self.event_queries.append(search)
            return 20
        if 'reactionmeddrapt.exact:"RASH"' in search:
            self.event_queries.append(search)
            return 12
        return 1000

    def fetch_count_buckets(self, search: str, count_field: str, limit: int = 100):
        raise requests.HTTPError("403 Client Error")


def test_fetch_global_baseline_falls_back_to_event_totals() -> None:
    client = _Client()

    baseline = fetch_global_baseline(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        observed_events=["NAUSEA", "RASH"],
    )

    assert baseline.total_reports == 1000
    assert baseline.event_counts == {"NAUSEA": 20, "RASH": 12}
    assert len(client.event_queries) == 2
