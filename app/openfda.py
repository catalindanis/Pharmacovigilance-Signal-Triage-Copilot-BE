from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable
from urllib.parse import urlencode

import requests


OPENFDA_BASE_URL = "https://api.fda.gov/drug/event.json"
LUCENE_SPECIAL_CHARS = ['\\', '+', '-', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '/']


@dataclass(frozen=True)
class OpenFDAQuery:
    drug_name: str
    start_date: date
    end_date: date
    limit: int = 100
    skip: int = 0

    def to_params(self) -> dict[str, str | int]:
        return {
            "search": build_openfda_search(self.drug_name, self.start_date, self.end_date),
            "limit": self.limit,
            "skip": self.skip,
        }


class OpenFDAClient:
    def __init__(self, base_url: str = OPENFDA_BASE_URL, timeout_seconds: int = 30) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def build_url(self, query: OpenFDAQuery) -> str:
        return f"{self.base_url}?{urlencode(query.to_params())}"

    def fetch_page(self, query: OpenFDAQuery) -> dict[str, Any]:
        response = requests.get(self.base_url, params=query.to_params(), timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def fetch_total_reports(self, search: str) -> int:
        params: dict[str, str | int] = {"search": search, "limit": 1, "skip": 0}
        response = requests.get(self.base_url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        return int(payload.get("meta", {}).get("results", {}).get("total", 0))

    def fetch_count_buckets(self, search: str, count_field: str, limit: int = 100) -> dict[str, int]:
        params: dict[str, str | int] = {
            "search": search,
            "count": count_field,
            "limit": limit,
        }
        response = requests.get(self.base_url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        buckets = payload.get("results", [])
        out: dict[str, int] = {}
        for item in buckets:
            term = str(item.get("term", "")).strip()
            if not term:
                continue
            out[term] = int(item.get("count", 0))
        return out

    def fetch_all_pages(self, query: OpenFDAQuery, max_pages: int | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        current_skip = query.skip
        page_number = 0

        while True:
            current_query = OpenFDAQuery(
                drug_name=query.drug_name,
                start_date=query.start_date,
                end_date=query.end_date,
                limit=query.limit,
                skip=current_skip,
            )
            payload = self.fetch_page(current_query)
            page_results = payload.get("results", [])

            if not page_results:
                break

            results.extend(page_results)

            if len(page_results) < query.limit:
                break

            page_number += 1
            if max_pages is not None and page_number >= max_pages:
                break

            current_skip += query.limit

        return results


def normalize_date_range(start_date: date, end_date: date) -> tuple[date, date]:
    if start_date > end_date:
        raise ValueError("start_date must be earlier than or equal to end_date")
    return start_date, end_date


def build_search_string(drug_name: str, start_date: date, end_date: date) -> str:
    query = OpenFDAQuery(drug_name=drug_name, start_date=start_date, end_date=end_date)
    return query.to_params()["search"]


def build_openfda_search(drug_name: str, start_date: date, end_date: date) -> str:
    escaped_drug_name = escape_search_term(drug_name)
    search_terms = [
        f'patient.drug.medicinalproduct:"{escaped_drug_name}"',
        f"receivedate:[{start_date:%Y%m%d} TO {end_date:%Y%m%d}]",
    ]
    return " AND ".join(search_terms)


def build_date_range_search(start_date: date, end_date: date) -> str:
    return f"receivedate:[{start_date:%Y%m%d} TO {end_date:%Y%m%d}]"


def build_event_search(event_term: str, start_date: date, end_date: date) -> str:
    escaped_event_term = escape_search_term(event_term)
    search_terms = [
        f'patient.reaction.reactionmeddrapt.exact:"{escaped_event_term}"',
        build_date_range_search(start_date, end_date),
    ]
    return " AND ".join(search_terms)


def build_drug_event_search(drug_name: str, event_term: str, start_date: date, end_date: date) -> str:
    escaped_drug_name = escape_search_term(drug_name)
    escaped_event_term = escape_search_term(event_term)
    search_terms = [
        f'patient.drug.medicinalproduct:"{escaped_drug_name}"',
        f'patient.reaction.reactionmeddrapt.exact:"{escaped_event_term}"',
        build_date_range_search(start_date, end_date),
    ]
    return " AND ".join(search_terms)


def escape_search_term(value: str) -> str:
    escaped = value
    for char in LUCENE_SPECIAL_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def collect_report_ids(records: Iterable[dict[str, Any]]) -> list[str]:
    report_ids: list[str] = []
    for record in records:
        report_id = record.get("safetyreportid")
        if report_id:
            report_ids.append(str(report_id))
    return report_ids
