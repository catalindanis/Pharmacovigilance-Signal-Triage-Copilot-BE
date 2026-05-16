from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class CleanCase:
    safetyreportid: str
    report_date: str
    drug: str
    reactions: List[str]
    country: str | None
    serious: bool
    raw: Dict[str, Any]
    patient_age: str | None
    patient_sex: str | None


def _parse_receivedate(raw_date: str) -> str:
    # openFDA uses YYYYMMDD in many fields; convert to ISO date where possible
    if not raw_date:
        return ""
    try:
        dt = datetime.strptime(raw_date, "%Y%m%d")
        return dt.date().isoformat()
    except Exception:
        return raw_date


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_cases_from_record(record: Dict[str, Any], match_drug_name: str | None = None) -> List[CleanCase]:
    """Extract one or more CleanCase objects from a single FAERS record.

    If match_drug_name is provided, only drugs whose medicinalproduct contains
    that string (case-insensitive) will be returned. Otherwise all drugs in the
    record are turned into cases.
    """
    patient = record.get("patient", {}) or {}
    drugs = patient.get("drug", []) or []
    reactions = patient.get("reaction", []) or []

    reaction_terms: List[str] = []
    for r in reactions:
        term = r.get("reactionmeddrapt") or r.get("reactionmeddrapt")
        if term:
            reaction_terms.append(term)

    cases: List[CleanCase] = []
    for d in drugs:
        med = d.get("medicinalproduct")
        if not med:
            continue
        if match_drug_name and match_drug_name.lower() not in med.lower():
            continue

        safetyreportid = record.get("safetyreportid") or ""
        received = record.get("receivedate") or record.get("receiptdate") or ""
        report_date = _parse_receivedate(received)
        country = record.get("occurcountry") or record.get("primarysourcecountry")
        serious_flag = record.get("serious")
        serious = serious_flag in ("1", 1, True, "true", "True")
        age = _normalize_optional_text(patient.get("patientonsetage") or record.get("patientonsetage"))
        sex = _normalize_optional_text(patient.get("patientsex") or record.get("patientsex"))

        cases.append(
            CleanCase(
                safetyreportid=str(safetyreportid),
                report_date=report_date,
                drug=med,
                reactions=reaction_terms,
                country=country,
                serious=serious,
                raw=record,
                patient_age=age,
                patient_sex=sex,
            )
        )

    return cases


def deduplicate_cases(cases: List[CleanCase]) -> List[CleanCase]:
    """Remove duplicate cases using report identity fields.

    Keeps the first occurrence of each unique tuple:
    (safetyreportid, report_date, patient_age, patient_sex).
    """
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: List[CleanCase] = []
    for case in cases:
        key = (case.safetyreportid, case.report_date, case.patient_age, case.patient_sex)
        if key not in seen:
            seen.add(key)
            result.append(case)
    return result
