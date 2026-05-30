import sqlite3
from typing import List
from app.transform import CleanCase

def get_connection(db_path: str = "faers_local.db") -> sqlite3.Connection:
    return sqlite3.connect(db_path)

def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            safetyreportid TEXT PRIMARY KEY,
            report_date TEXT,
            drug TEXT,
            country TEXT,
            serious BOOLEAN,
            patient_age TEXT,
            patient_sex TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reactions (
            safetyreportid TEXT,
            reaction TEXT,
            FOREIGN KEY (safetyreportid) REFERENCES cases (safetyreportid),
            PRIMARY KEY (safetyreportid, reaction)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_drug ON cases(drug)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON cases(report_date)')

    conn.commit()


def bulk_insert_cases(conn: sqlite3.Connection, cases: List[CleanCase]) -> None:
    cursor = conn.cursor()

    case_data = []
    reaction_data = []

    for c in cases:
        case_data.append((
            c.safetyreportid, c.report_date, c.drug,
            c.country, c.serious, c.patient_age, c.patient_sex
        ))
        for r in c.reactions:
            reaction_data.append((c.safetyreportid, r))

    cursor.executemany('''
        INSERT OR IGNORE INTO cases 
        (safetyreportid, report_date, drug, country, serious, patient_age, patient_sex)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', case_data)

    cursor.executemany('''
        INSERT OR IGNORE INTO reactions (safetyreportid, reaction)
        VALUES (?, ?)
    ''', reaction_data)

    conn.commit()