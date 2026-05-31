from __future__ import annotations

import argparse
import json
from datetime import datetime, date
from math import isinf
from typing import Any

from .baseline import fetch_global_baseline
from .openfda import OpenFDAClient, OpenFDAQuery, normalize_date_range
from .signals import build_signal_metrics
from .trend import build_monthly_event_counts, detect_event_trends
from .transform import CleanCase, extract_cases_from_record, deduplicate_cases
from .rxnorm import RxNormClient
from database.db_manager import fetch_cases_from_db


def parse_date(s: str) -> date:
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    raise ValueError(f"Invalid date format: {s}. Use YYYY-MM-DD or YYYYMMDD")


SAMPLE_RECORD = {
    "safetyreportid": "demo-1",
    "receivedate": "20240115",
    "occurcountry": "US",
    "serious": "1",
    "patient": {
        "drug": [{"medicinalproduct": "Ibuprofen 200mg"}],
        "reaction": [{"reactionmeddrapt": "NAUSEA"}],
    },
}


def run_demo(drug_name: str, start: date, end: date, limit: int) -> None:
    print("Running in demo mode (no network). Using sample record.")
    records = [SAMPLE_RECORD]
    cases = []
    for r in records:
        cases.extend(extract_cases_from_record(r, match_drug_name=drug_name))

    cases = deduplicate_cases(cases)
    print(json.dumps([c.__dict__ for c in cases], indent=2, ensure_ascii=False))


def _build_serious_event_counts(cases: list[CleanCase]) -> dict[str, int]:
    serious_counts: dict[str, int] = {}
    for case in cases:
        if not case.serious:
            continue
        for event in set(case.reactions):
            serious_counts[event] = serious_counts.get(event, 0) + 1
    return serious_counts


def _build_event_counts(cases: list[CleanCase]) -> dict[str, int]:
    event_counts: dict[str, int] = {}
    for case in cases:
        for event in set(case.reactions):
            if not event:
                continue
            event_counts[event] = event_counts.get(event, 0) + 1
    return event_counts


def run_live(
    drug_name: str,
    start: date,
    end: date,
    limit: int,
    max_pages: int | None,
    normalize: bool = False,
    normalize_reactions: bool = False,
    stage2: bool = False,
    top_signals: int = 20,
    use_local_db: bool = False,
) -> None:
    client = OpenFDAClient()
    cases = []

    if use_local_db:
        print("Normalizing input...")
        rx_client = RxNormClient()
        norm_result = rx_client.normalize_name(drug_name)

        search_substance = norm_result.generic_name.upper() if norm_result.generic_name else drug_name.upper()

        print(f"Querying database for '{search_substance}' from {start} to {end}")
        cases = fetch_cases_from_db("faers_local.db", search_substance, start, end)
        print(f"Fetched {len(cases)} cases")
    else:
        q = OpenFDAQuery(drug_name=drug_name, start_date=start, end_date=end, limit=limit, skip=0)
        print(f"Querying openFDA for '{drug_name}' from {start} to {end} (limit={limit})")

        records = client.fetch_all_pages(q, max_pages=max_pages)
        print(f"Fetched {len(records)} raw records")

        for r in records:
            cases.extend(extract_cases_from_record(r, match_drug_name=drug_name))

        cases = deduplicate_cases(cases)
        print(f"Extracted {len(cases)} unique cases (after deduplication)")

    if stage2:
        print("Running phase 2 signal detection...")

        drug_event_counts = _build_event_counts(cases)
        drug_total_reports = len(cases)
        candidate_events = sorted(event for event, count in drug_event_counts.items() if count >= 3)
        global_baseline = fetch_global_baseline(
            client,
            start,
            end,
            observed_events=candidate_events,
        )

        serious_event_counts = _build_serious_event_counts(cases)
        signal_metrics = build_signal_metrics(
            drug_event_counts=drug_event_counts,
            all_event_counts=global_baseline.event_counts,
            serious_event_counts=serious_event_counts,
            n_drug_total=drug_total_reports,
            n_all_total=global_baseline.total_reports,
        )

        trend_map = detect_event_trends(build_monthly_event_counts(cases))

        output_signals = []
        for metric in signal_metrics[:top_signals]:
            trend = trend_map.get(metric.event)
            growth = None
            if trend is not None:
                growth = "inf" if isinf(trend.growth_ratio) else round(trend.growth_ratio, 4)

            output_signals.append(
                {
                    "event": metric.event,
                    "n_drug_event": metric.n_drug_event,
                    "n_drug_total": metric.n_drug_total,
                    "n_all_event": metric.n_all_event,
                    "n_all_total": metric.n_all_total,
                    "prr": round(metric.prr, 4),
                    "ror": "inf" if isinf(metric.ror) else round(metric.ror, 4),
                    "chi_square_yates": round(metric.chi_square_yates, 4),
                    "serious_ratio": round(metric.serious_ratio, 4),
                    "frequency_ratio": round(metric.frequency_ratio, 4),
                    "score": round(metric.score, 4),
                    "valid_signal": metric.valid_signal,
                    "trend": {
                        "latest_month": trend.latest_month if trend else None,
                        "latest_count": trend.latest_count if trend else 0,
                        "baseline_average": round(trend.baseline_average, 4) if trend else 0.0,
                        "growth_ratio": growth,
                        "emerging": trend.emerging if trend else False,
                    },
                }
            )

        payload = {
            "drug": drug_name,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "drug_total_reports": drug_total_reports,
            "global_total_reports": global_baseline.total_reports,
            "signal_count": len(signal_metrics),
            "signals": output_signals,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    norm_cache: dict[str, dict] = {}
    rx: RxNormClient | None = None
    if normalize:
        rx = RxNormClient()

    def get_norm(drug: str) -> dict:
        if drug in norm_cache:
            return norm_cache[drug]
        if rx is None:
            obj = {"original": drug, "rxcui": None, "generic_rxcui": None, "generic_name": None}
        else:
            res = rx.normalize_name(drug)
            obj = {"original": res.original, "rxcui": res.rxcui, "generic_rxcui": res.generic_rxcui, "generic_name": res.generic_name}
        norm_cache[drug] = obj
        return obj

    out = []
    for c in cases[:10]:
        entry = {
            "safetyreportid": c.safetyreportid,
            "report_date": c.report_date,
            "drug": c.drug,
            "reactions": c.reactions,
            "country": c.country,
            "serious": c.serious,
        }
        if normalize:
            entry["normalized"] = get_norm(c.drug)
        out.append(entry)

    print(json.dumps(out, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch and extract FAERS cases (phase 1)")
    parser.add_argument("--drug", required=True, help="Drug name to search for")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD) or YYYYMMDD")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD) or YYYYMMDD")
    parser.add_argument("--limit", type=int, default=100, help="page size (limit) for openFDA requests")
    parser.add_argument("--max-pages", type=int, default=None, help="max pages to fetch (for testing)")
    parser.add_argument("--demo", action="store_true", help="Run demo mode without network calls")
    parser.add_argument("--normalize", action="store_true", help="Normalize drug names via RxNorm")
    parser.add_argument("--stage2", action="store_true", help="Run phase 2 signal detection (PRR/ROR/trend)")
    parser.add_argument("--top-signals", type=int, default=20, help="Number of top signals to output in stage 2")
    parser.add_argument("--local-db", action="store_true", help="Use local database")

    args = parser.parse_args(argv)

    start = parse_date(args.start)
    end = parse_date(args.end)
    normalize_date_range(start, end)

    if args.demo:
        run_demo(args.drug, start, end, args.limit)
    else:
        run_live(
            args.drug,
            start,
            end,
            args.limit,
            args.max_pages,
            normalize=args.normalize,
            stage2=args.stage2,
            top_signals=args.top_signals,
            use_local_db=args.local_db
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
