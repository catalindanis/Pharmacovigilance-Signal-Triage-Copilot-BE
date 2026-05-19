from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .transform import CleanCase


@dataclass(frozen=True)
class TrendInfo:
    event: str
    months: dict[str, int]
    baseline_average: float
    latest_month: str | None
    latest_count: int
    growth_ratio: float
    emerging: bool


def to_month_bucket(iso_date: str) -> str | None:
    if not iso_date:
        return None
    try:
        parsed = datetime.strptime(iso_date, "%Y-%m-%d")
    except Exception:
        return None
    return f"{parsed.year:04d}-{parsed.month:02d}"


def _month_sequence(months: list[str]) -> list[str]:
    if not months:
        return []

    first = datetime.strptime(months[0], "%Y-%m")
    last = datetime.strptime(months[-1], "%Y-%m")

    values: list[str] = []
    y = first.year
    m = first.month
    while (y < last.year) or (y == last.year and m <= last.month):
        values.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return values


def build_monthly_event_counts(cases: list[CleanCase]) -> dict[str, dict[str, int]]:
    month_event_reports: dict[str, set[tuple[str, str]]] = defaultdict(set)

    for case in cases:
        month = to_month_bucket(case.report_date)
        if month is None:
            continue

        report_id = case.safetyreportid or ""
        if not report_id:
            continue

        for event in set(case.reactions):
            if event:
                month_event_reports[event].add((month, report_id))

    counts: dict[str, dict[str, int]] = {}
    for event, month_report_pairs in month_event_reports.items():
        months: dict[str, int] = defaultdict(int)
        for month, _report in month_report_pairs:
            months[month] += 1

        ordered_keys = sorted(months.keys())
        full_sequence = _month_sequence(ordered_keys)
        counts[event] = {month: months.get(month, 0) for month in full_sequence}

    return counts


def detect_event_trends(monthly_event_counts: dict[str, dict[str, int]]) -> dict[str, TrendInfo]:
    trends: dict[str, TrendInfo] = {}

    for event, month_counts in monthly_event_counts.items():
        month_keys = sorted(month_counts.keys())
        if not month_keys:
            trends[event] = TrendInfo(
                event=event,
                months={},
                baseline_average=0.0,
                latest_month=None,
                latest_count=0,
                growth_ratio=0.0,
                emerging=False,
            )
            continue

        latest_month = month_keys[-1]
        latest_count = month_counts.get(latest_month, 0)

        previous_counts = [month_counts[m] for m in month_keys[:-1]]
        if previous_counts:
            baseline_average = sum(previous_counts) / len(previous_counts)
        else:
            baseline_average = 0.0

        if baseline_average > 0:
            growth_ratio = (latest_count - baseline_average) / baseline_average
        elif latest_count > 0:
            growth_ratio = float("inf")
        else:
            growth_ratio = 0.0

        emerging = latest_count >= 3 and (
            (baseline_average == 0 and latest_count > 0)
            or (baseline_average > 0 and growth_ratio >= 1.0)
        )

        trends[event] = TrendInfo(
            event=event,
            months=month_counts,
            baseline_average=baseline_average,
            latest_month=latest_month,
            latest_count=latest_count,
            growth_ratio=growth_ratio,
            emerging=emerging,
        )

    return trends
