import sqlite3
from typing import List
from app.transform import CleanCase
from datetime import date

def get_connection(db_path: str = "faers_local.db") -> sqlite3.Connection:
    return sqlite3.connect(db_path)

def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            safetyreportid TEXT PRIMARY KEY,
            report_date TEXT,
            drug TEXT,
            substance TEXT,
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_substance ON cases(substance)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON cases(report_date)')

    conn.commit()


def bulk_insert_cases(conn: sqlite3.Connection, cases: List[CleanCase]) -> None:
    cursor = conn.cursor()

    case_data = []
    reaction_data = []

    for c in cases:
        case_data.append((
            c.safetyreportid, c.report_date, c.drug, c.substance,
            c.country, c.serious, c.patient_age, c.patient_sex
        ))
        for r in c.reactions:
            reaction_data.append((c.safetyreportid, r))

    cursor.executemany('''
        INSERT OR IGNORE INTO cases 
        (safetyreportid, report_date, drug, substance, country, serious, patient_age, patient_sex)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', case_data)

    cursor.executemany('''
        INSERT OR IGNORE INTO reactions (safetyreportid, reaction)
        VALUES (?, ?)
    ''', reaction_data)

    conn.commit()


def fetch_cases_from_db(conn: sqlite3.Connection, substance_name: str, start_date: date, end_date: date) -> List[CleanCase]:
    cursor = conn.cursor()

    query = '''
        SELECT c.safetyreportid, c.report_date, c.drug, c.substance,
               c.country, c.serious, c.patient_age, c.patient_sex,
               GROUP_CONCAT(r.reaction, '|') as reactions
        FROM cases c
        LEFT JOIN reactions r ON c.safetyreportid = r.safetyreportid
        WHERE c.substance = ? AND c.report_date BETWEEN ? AND ?
        GROUP BY c.safetyreportid
    '''

    cursor.execute(query, (substance_name.upper(), start_date.isoformat(), end_date.isoformat()))
    rows = cursor.fetchall()

    cases = []
    for row in rows:
        reactions_list = row[8].split('|') if row[8] else []

        c = CleanCase(
            safetyreportid=row[0],
            report_date=row[1],
            drug=row[2],
            substance=row[3],
            country=row[4],
            serious=bool(row[5]),
            patient_age=row[6],
            patient_sex=row[7],
            reactions=reactions_list,
            raw={}
        )
        cases.append(c)

    return cases