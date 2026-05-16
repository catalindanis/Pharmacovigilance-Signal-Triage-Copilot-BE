from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import requests

from .openfda import OpenFDAClient, build_date_range_search, build_event_search, build_openfda_search

REACTION_FIELD = "patient.reaction.reactionmeddrapt.exact"


@dataclass(frozen=True)
class GlobalBaseline:
    total_reports: int
    event_counts: dict[str, int]


@dataclass(frozen=True)
class DrugWindowStats:
    total_reports: int
    event_counts: dict[str, int]


def fetch_global_baseline(
    client: OpenFDAClient,
    start_date: date,
    end_date: date,
    observed_events: list[str] | None = None,
    event_count_limit: int = 1000,
) -> GlobalBaseline:
    search = build_date_range_search(start_date, end_date)
    total_reports = client.fetch_total_reports(search)

    try:
        event_counts = client.fetch_count_buckets(
            search=search,
            count_field=REACTION_FIELD,
            limit=event_count_limit,
        )
    except requests.RequestException:
        if not observed_events:
            raise
        event_counts = {}
        for event in observed_events:
            event_search = build_event_search(event, start_date, end_date)
            event_counts[event] = client.fetch_total_reports(event_search)

    return GlobalBaseline(total_reports=total_reports, event_counts=event_counts)


def fetch_drug_window_stats(
    client: OpenFDAClient,
    drug_name: str,
    start_date: date,
    end_date: date,
    event_count_limit: int = 1000,
) -> DrugWindowStats:
    search = build_openfda_search(drug_name, start_date, end_date)
    total_reports = client.fetch_total_reports(search)
    event_counts = client.fetch_count_buckets(
        search=search,
        count_field=REACTION_FIELD,
        limit=event_count_limit,
    )
    return DrugWindowStats(total_reports=total_reports, event_counts=event_counts)
