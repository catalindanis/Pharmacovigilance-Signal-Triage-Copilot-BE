from app.transform import CleanCase, extract_cases_from_record, deduplicate_cases


def make_sample_record() -> dict:
    return {
        "safetyreportid": "12345-1",
        "receivedate": "20240115",
        "occurcountry": "US",
        "serious": "1",
        "patientonsetage": "54",
        "patientsex": "1",
        "patient": {
            "drug": [
                {"medicinalproduct": "Ibuprofen 200mg", "drugcharacterization": "2"}
            ],
            "reaction": [
                {"reactionmeddrapt": "NAUSEA"},
                {"reactionmeddrapt": "HEADACHE"},
            ],
        },
    }


def test_extract_cases_basic() -> None:
    record = make_sample_record()
    cases = extract_cases_from_record(record, match_drug_name="ibuprofen")

    assert isinstance(cases, list)
    assert len(cases) == 1
    c = cases[0]
    assert isinstance(c, CleanCase)
    assert c.safetyreportid == "12345-1"
    assert c.report_date == "2024-01-15"
    assert "Ibuprofen" in c.drug
    assert "NAUSEA" in c.reactions
    assert c.country == "US"
    assert c.serious is True
    assert c.patient_age == "54"
    assert c.patient_sex == "1"


def test_extract_cases_no_match() -> None:
    record = make_sample_record()
    cases = extract_cases_from_record(record, match_drug_name="paracetamol")
    assert cases == []


def test_deduplicate_cases_empty() -> None:
    result = deduplicate_cases([])
    assert result == []


def test_deduplicate_cases_no_duplicates() -> None:
    case1 = CleanCase(
        safetyreportid="id-1",
        report_date="2024-01-15",
        drug="Ibuprofen",
        reactions=["NAUSEA"],
        country="US",
        serious=True,
        raw={},
        patient_age="54",
        patient_sex="1",
    )
    case2 = CleanCase(
        safetyreportid="id-2",
        report_date="2024-01-16",
        drug="Paracetamol",
        reactions=["HEADACHE"],
        country="UK",
        serious=False,
        raw={},
        patient_age="23",
        patient_sex="2",
    )
    result = deduplicate_cases([case1, case2])
    assert len(result) == 2
    assert result[0].safetyreportid == "id-1"
    assert result[1].safetyreportid == "id-2"


def test_deduplicate_cases_with_duplicates() -> None:
    case1 = CleanCase(
        safetyreportid="id-1",
        report_date="2024-01-15",
        drug="Ibuprofen",
        reactions=["NAUSEA"],
        country="US",
        serious=True,
        raw={},
        patient_age="54",
        patient_sex="1",
    )
    case1_dup = CleanCase(
        safetyreportid="id-1",  # same id
        report_date="2024-01-15",
        drug="Ibuprofen 400mg",
        reactions=["NAUSEA"],
        country="US",
        serious=True,
        raw={},
        patient_age="54",
        patient_sex="1",
    )
    case2 = CleanCase(
        safetyreportid="id-2",
        report_date="2024-01-16",
        drug="Paracetamol",
        reactions=["HEADACHE"],
        country="UK",
        serious=False,
        raw={},
        patient_age="23",
        patient_sex="2",
    )
    result = deduplicate_cases([case1, case1_dup, case2])
    assert len(result) == 2
    assert result[0].safetyreportid == "id-1"
    assert result[1].safetyreportid == "id-2"


def test_deduplicate_cases_same_report_different_patient_identity_kept() -> None:
    case1 = CleanCase(
        safetyreportid="id-1",
        report_date="2024-01-15",
        drug="Ibuprofen",
        reactions=["NAUSEA"],
        country="US",
        serious=True,
        raw={},
        patient_age="54",
        patient_sex="1",
    )
    case2 = CleanCase(
        safetyreportid="id-1",
        report_date="2024-01-15",
        drug="Ibuprofen",
        reactions=["NAUSEA"],
        country="US",
        serious=True,
        raw={},
        patient_age="55",
        patient_sex="1",
    )

    result = deduplicate_cases([case1, case2])
    assert len(result) == 2
