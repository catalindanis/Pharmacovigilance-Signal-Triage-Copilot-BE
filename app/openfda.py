from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable
from urllib.parse import urlencode

import requests


OPENFDA_BASE_URL = "https://api.fda.gov/drug/event.json"


@dataclass(frozen=True)
class OpenFDAQuery:
    drug_name: str
    start_date: date
    end_date: date
    limit: int = 100
    skip: int = 0

    def to_params(self) -> dict[str, str | int]:
        search_terms = [
            f'patient.drug.medicinalproduct:"{self.drug_name}"',
            f"receivedate:[{self.start_date:%Y%m%d} TO {self.end_date:%Y%m%d}]",
        ]

        return {
            "search": " AND ".join(search_terms),
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


def collect_report_ids(records: Iterable[dict[str, Any]]) -> list[str]:
    report_ids: list[str] = []
    for record in records:
        report_id = record.get("safetyreportid")
        if report_id:
            report_ids.append(str(report_id))
    return report_ids
