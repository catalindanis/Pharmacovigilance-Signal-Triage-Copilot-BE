from __future__ import annotations

import argparse
import json
from datetime import datetime, date
from typing import Any

from .openfda import OpenFDAClient, OpenFDAQuery, normalize_date_range
from .transform import extract_cases_from_record, deduplicate_cases
from .rxnorm import RxNormClient


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


def run_live(drug_name: str, start: date, end: date, limit: int, max_pages: int | None, normalize: bool = False, normalize_reactions: bool = False) -> None:
    client = OpenFDAClient()
    q = OpenFDAQuery(drug_name=drug_name, start_date=start, end_date=end, limit=limit, skip=0)
    print(f"Querying openFDA for '{drug_name}' from {start} to {end} (limit={limit})")

    records = client.fetch_all_pages(q, max_pages=max_pages)
    print(f"Fetched {len(records)} raw records")

    cases = []
    for r in records:
        cases.extend(extract_cases_from_record(r, match_drug_name=drug_name))

    cases = deduplicate_cases(cases)
    print(f"Extracted {len(cases)} unique cases (after deduplication)")

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

    args = parser.parse_args(argv)

    start = parse_date(args.start)
    end = parse_date(args.end)
    normalize_date_range(start, end)

    if args.demo:
        run_demo(args.drug, start, end, args.limit)
    else:
        run_live(args.drug, start, end, args.limit, args.max_pages, normalize=args.normalize)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
