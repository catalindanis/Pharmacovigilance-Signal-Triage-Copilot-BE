from datetime import date

from app.openfda import OpenFDAClient, OpenFDAQuery, build_search_string, normalize_date_range


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
