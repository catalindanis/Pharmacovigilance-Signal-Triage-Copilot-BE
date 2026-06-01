from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sqlite3


@dataclass(frozen=True)
class GlobalBaseline:
    total_reports: int
    event_counts: dict[str, int]


@dataclass(frozen=True)
class DrugWindowStats:
    total_reports: int
    event_counts: dict[str, int]


def fetch_global_baseline(
        conn: sqlite3.Connection,
        start_date: date,
        end_date: date,
        event_count_limit: int = 1000,
) -> GlobalBaseline:
    cursor = conn.cursor()

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    cursor.execute('''
        SELECT COUNT(DISTINCT safetyreportid)
        FROM cases
        WHERE report_date BETWEEN ? AND ?
        ''', (start_str, end_str))
    total_reports = cursor.fetchone()[0] or 0

    cursor.execute('''
       SELECT r.reaction, COUNT(DISTINCT c.safetyreportid) as count
       FROM reactions r
                JOIN cases c ON r.safetyreportid = c.safetyreportid
       WHERE c.report_date BETWEEN ? AND ?
       GROUP BY r.reaction
       ORDER BY count DESC
       LIMIT ?
       ''', (start_str, end_str, event_count_limit))

    event_counts = {row[0]: row[1] for row in cursor.fetchall()}

    return GlobalBaseline(total_reports=total_reports, event_counts=event_counts)