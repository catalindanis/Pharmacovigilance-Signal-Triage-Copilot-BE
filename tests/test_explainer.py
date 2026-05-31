from __future__ import annotations

from app.explainer import (
    GeminiSignalExplainer,
    SignalEvidencePacket,
    build_signal_packet_prompt,
    generate_signal_packet,
    generate_signal_packets,
)


def make_payload() -> dict:
    return {
        "drug": "Ibuprofen",
        "signals": [
            {
                "event": "HAEMATEMESIS",
                "n_drug_event": 4,
                "n_drug_total": 100,
                "n_all_event": 12,
                "n_all_total": 1000,
                "prr": 246.3692,
                "ror": 355.4829,
                "chi_square_yates": 748.4573,
                "serious_ratio": 0.75,
                "frequency_ratio": 0.04,
                "score": 0.326,
                "valid_signal": True,
                "trend": {"latest_month": "2024-03", "latest_count": 3, "baseline_average": 1.0, "growth_ratio": 3.0, "emerging": True},
            },
            {
                "event": "NAUSEA",
                "n_drug_event": 8,
                "n_drug_total": 100,
                "n_all_event": 200,
                "n_all_total": 1000,
                "prr": 1.2,
                "ror": 1.1,
                "chi_square_yates": 2.0,
                "serious_ratio": 0.1,
                "frequency_ratio": 0.08,
                "score": 0.088,
                "valid_signal": False,
                "trend": {"latest_month": "2024-03", "latest_count": 1, "baseline_average": 1.0, "growth_ratio": 1.0, "emerging": False},
            },
        ],
    }


def test_build_signal_packet_prompt_includes_signal_details() -> None:
    payload = make_payload()

    event_name, prompt = build_signal_packet_prompt(payload, signal_index=0)

    assert event_name == "HAEMATEMESIS"
    assert "Ibuprofen" in prompt
    assert "PRR: 246.3692" in prompt
    assert "Trend:" in prompt
    assert "emerging" in prompt


def test_generate_signal_packets_uses_env_file_values(monkeypatch) -> None:
    payload = make_payload()

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("PV_LLM_MODEL", raising=False)
    monkeypatch.setattr("app.explainer._load_env_file", lambda _path: {"GOOGLE_API_KEY": "env-key", "PV_LLM_MODEL": "gemini-3.5-flash"})

    class _FakeExplainer:
        def __init__(self, api_key: str | None = None, model: str | None = None):
            self.api_key = api_key
            self.model = model

        def generate_packet(self, signals_json: dict, signal_index: int = 0):
            signal = signals_json["signals"][signal_index]
            return SignalEvidencePacket(drug=signals_json["drug"], event=signal["event"], markdown=f"{self.api_key}:{self.model}:{signal_index}")

    monkeypatch.setattr("app.explainer.GeminiSignalExplainer", _FakeExplainer)

    packets = generate_signal_packets(payload, api_key=None, model=None)

    assert [packet.markdown for packet in packets] == ["env-key:gemini-3.5-flash:0", "env-key:gemini-3.5-flash:1"]


def test_generate_signal_packet_returns_empty_message_for_no_signals() -> None:
    assert generate_signal_packet({"drug": "Ibuprofen", "signals": []}, api_key="test-key") == "No valid signals found to analyze."


def test_gemini_signal_explainer_renders_structured_packet() -> None:
    payload = make_payload()

    explainer = GeminiSignalExplainer(api_key="test-key", model="gemini-3.5-flash")
    packet = explainer.generate_packet(payload, signal_index=1)

    assert isinstance(packet, SignalEvidencePacket)
    assert packet.drug == "Ibuprofen"
    assert packet.event == "NAUSEA"
    assert "### Signal 2: NAUSEA" in packet.markdown
    assert "#### 1. Medical Context" in packet.markdown
    assert "#### 2. Statistical Justification" in packet.markdown
    assert "#### 3. Trend Analysis" in packet.markdown
    assert "#### 4. Literature References" in packet.markdown
    assert "#### 5. Priority & Recommendation" in packet.markdown
    assert "**Priority**: LOW" in packet.markdown
    assert "No specific literature references were found" in packet.markdown


def test_generate_signal_packets_returns_packets_for_all_signals(monkeypatch) -> None:
    payload = make_payload()

    class _FakeExplainer:
        def __init__(self, api_key: str | None = None, model: str | None = None):
            self.api_key = api_key
            self.model = model

        def generate_packet(self, signals_json: dict, signal_index: int = 0):
            signal = signals_json["signals"][signal_index]
            return SignalEvidencePacket(drug=signals_json["drug"], event=signal["event"], markdown=f"{self.api_key}:{self.model}:packet-{signal_index}")

    monkeypatch.setattr("app.explainer.GeminiSignalExplainer", _FakeExplainer)

    packets = generate_signal_packets(payload, api_key="test-key", model="gemini-3.5-flash")

    assert [packet.event for packet in packets] == ["HAEMATEMESIS", "NAUSEA"]
    assert [packet.markdown for packet in packets] == ["test-key:gemini-3.5-flash:packet-0", "test-key:gemini-3.5-flash:packet-1"]