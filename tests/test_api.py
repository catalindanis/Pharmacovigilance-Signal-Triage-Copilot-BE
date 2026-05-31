from __future__ import annotations

from fastapi.testclient import TestClient

import app.api as api_module
from app.api import app


client = TestClient(app)


def make_payload() -> dict:
    return {
        "drug": "Ibuprofen",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
    }


def make_stage2_payload() -> dict:
    return {
        "drug": "Ibuprofen",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "drug_total_reports": 15,
        "global_total_reports": 1508,
        "signal_count": 2,
        "signals": [
            {
                "event": "OFF LABEL USE",
                "n_drug_event": 4,
                "n_drug_total": 15,
                "n_all_event": 82,
                "n_all_total": 1508,
                "prr": 4.9041,
                "ror": 6.5967,
                "chi_square_yates": 9.4362,
                "serious_ratio": 1.0,
                "frequency_ratio": 0.2667,
                "score": 0.56,
                "valid_signal": True,
                "trend": {"latest_month": "2024-01", "latest_count": 4, "baseline_average": 0.0, "growth_ratio": "inf", "emerging": True},
            },
            {
                "event": "PAIN",
                "n_drug_event": 3,
                "n_drug_total": 15,
                "n_all_event": 42,
                "n_all_total": 1508,
                "prr": 7.181,
                "ror": 9.3205,
                "chi_square_yates": 10.7827,
                "serious_ratio": 0.6667,
                "frequency_ratio": 0.2,
                "score": 0.3867,
                "valid_signal": True,
                "trend": {"latest_month": "2024-01", "latest_count": 3, "baseline_average": 0.0, "growth_ratio": "inf", "emerging": True},
            },
        ],
    }


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_explain_endpoint_returns_json_packets(monkeypatch) -> None:
    payload = make_payload()
    stage2_payload = make_stage2_payload()

    expected_packets = [
        {
            "signal_index": 0,
            "drug": "Ibuprofen",
            "event": "OFF LABEL USE",
            "event_title": "OFF LABEL USE",
            "medical_context": "mc-0",
            "statistical_justification": "sj-0",
            "trend_analysis": "ta-0",
            "literature_references": [],
            "priority": "HIGH",
            "next_steps": "ns-0",
            "markdown": "md-0",
        },
        {
            "signal_index": 1,
            "drug": "Ibuprofen",
            "event": "PAIN",
            "event_title": "PAIN",
            "medical_context": "mc-1",
            "statistical_justification": "sj-1",
            "trend_analysis": "ta-1",
            "literature_references": ["https://pubmed.ncbi.nlm.nih.gov/123"],
            "priority": "MEDIUM",
            "next_steps": "ns-1",
            "markdown": "md-1",
        },
    ]

    def fake_build_stage2_payload(**kwargs) -> dict:
        assert kwargs["drug_name"] == payload["drug"]
        assert kwargs["start"].isoformat() == payload["start_date"]
        assert kwargs["end"].isoformat() == payload["end_date"]
        return stage2_payload

    def fake_generate_signal_packet_payloads(_payload: dict) -> list[dict]:
        assert _payload["drug"] == stage2_payload["drug"]
        assert len(_payload["signals"]) == 2
        return expected_packets

    monkeypatch.setattr(api_module, "build_stage2_payload", fake_build_stage2_payload)
    monkeypatch.setattr(api_module, "generate_signal_packet_payloads", fake_generate_signal_packet_payloads)

    response = client.post("/api/explain", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["drug"] == "Ibuprofen"
    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2024-01-31"
    assert data["signal_count"] == 2
    assert data["packets"] == expected_packets
