from datetime import date

from app.openfda import (
    OpenFDAClient,
    build_drug_event_search,
    OpenFDAQuery,
    build_date_range_search,
    escape_search_term,
    build_event_search,
    build_search_string,
    normalize_date_range,
)


def test_build_search_string_includes_drug_and_date_range() -> None:
    search = build_search_string("ibuprofen", date(2024, 1, 1), date(2024, 12, 31))

    assert 'patient.drug.medicinalproduct:"ibuprofen"' in search
    assert "receivedate:[20240101 TO 20241231]" in search


def test_query_to_params_contains_pagination() -> None:
    query = OpenFDAQuery(
        drug_name="ibuprofen",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        limit=50,
        skip=100,
    )

    params = query.to_params()

    assert params["limit"] == 50
    assert params["skip"] == 100


def test_normalize_date_range_rejects_inverted_range() -> None:
    try:
        normalize_date_range(date(2024, 12, 31), date(2024, 1, 1))
    except ValueError as exc:
        assert "start_date" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_build_url_contains_query_values() -> None:
    client = OpenFDAClient(base_url="https://example.test/api")
    query = OpenFDAQuery(
        drug_name="ibuprofen",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        limit=25,
        skip=50,
    )

    url = client.build_url(query)

    assert url.startswith("https://example.test/api?")
    assert "limit=25" in url
    assert "skip=50" in url


class _DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_build_date_range_search() -> None:
    search = build_date_range_search(date(2024, 1, 1), date(2024, 1, 31))
    assert search == "receivedate:[20240101 TO 20240131]"


def test_build_event_search() -> None:
    search = build_event_search("NAUSEA", date(2024, 1, 1), date(2024, 1, 31))
    assert 'patient.reaction.reactionmeddrapt.exact:"NAUSEA"' in search
    assert "receivedate:[20240101 TO 20240131]" in search


def test_build_drug_event_search() -> None:
    search = build_drug_event_search("ibuprofen", "NAUSEA", date(2024, 1, 1), date(2024, 1, 31))
    assert 'patient.drug.medicinalproduct:"ibuprofen"' in search
    assert 'patient.reaction.reactionmeddrapt.exact:"NAUSEA"' in search


def test_escape_search_term_escapes_lucene_characters() -> None:
    escaped = escape_search_term('Crohn^s disease / test')
    assert escaped == 'Crohn\\^s disease \\/ test'


def test_fetch_total_reports_uses_meta_total(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return _DummyResponse({"meta": {"results": {"total": 321}}})

    monkeypatch.setattr("app.openfda.requests.get", fake_get)
    client = OpenFDAClient(base_url="https://example.test/api")

    total = client.fetch_total_reports('patient.drug.medicinalproduct:"ibuprofen"')
    assert total == 321


def test_fetch_count_buckets_returns_term_counts(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return _DummyResponse(
            {
                "results": [
                    {"term": "NAUSEA", "count": 12},
                    {"term": "HEADACHE", "count": 8},
                ]
            }
        )

    monkeypatch.setattr("app.openfda.requests.get", fake_get)
    client = OpenFDAClient(base_url="https://example.test/api")

    buckets = client.fetch_count_buckets("receivedate:[20240101 TO 20240131]", "patient.reaction.reactionmeddrapt.exact")
    assert buckets == {"NAUSEA": 12, "HEADACHE": 8}
