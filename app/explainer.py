from __future__ import annotations

import json
import requests
from typing import Any

SYSTEM_PROMPT = """
You are an expert Pharmacovigilance (PV) Data Scientist and Medical Reviewer.
Analyze the provided statistical disproportionate reporting signals (PRR, ROR) for the specific drug.

You MUST respond strictly in valid JSON format matching this exact structure:
{
    "medical_context": "Brief explanation of the adverse event and potential severity.",
    "statistical_justification": "Explanation of PRR, ROR, and Yates' Chi-Square scores.",
    "trend_analysis": "Mention if the signal is emerging or stable.",
    "priority": "HIGH, MEDIUM, or LOW",
    "next_steps": "Actionable recommendation for the safety team.",
    "literature_references": ["list", "of", "strings", "or", "empty list"],
}
Do not include any other text outside the JSON block.
""".strip()


def build_signal_packet_data(signals_json: dict[str, Any], signal_index: int = 0) -> dict[str, Any]:
    signals = signals_json.get("signals") or []
    if signal_index < 0 or signal_index >= len(signals):
        raise IndexError("signal_index is out of range for the provided payload")

    signal = signals[signal_index]
    drug_name = signals_json.get("drug", "Unknown drug")
    event_title = signal.get("event", "Unknown event").strip().upper()

    llm_input_data = {
        "drug": drug_name,
        "event": event_title,
        "prr": signal.get("prr", 0),
        "ror": signal.get("ror", 0),
        "chi_square_yates": signal.get("chi_square_yates", 0),
        "trend": signal.get("trend", {})
    }

    ollama_url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llm-model",
        "system": SYSTEM_PROMPT,
        "prompt": json.dumps(llm_input_data),
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(ollama_url, json=payload, timeout=120)
        response.raise_for_status()
        result_text = response.json().get("response", "{}")
        llm_output = json.loads(result_text)
    except Exception as e:
        print(f"Eroare la generarea LLM: {e}")
        llm_output = {
            "medical_context": "Error generating context.",
            "statistical_justification": "Error generating justification.",
            "trend_analysis": "Error analyzing trend.",
            "priority": "UNKNOWN",
            "next_steps": "Manual review required.",
            "literature_references": [],
        }

    return {
        "signal_index": signal_index,
        "drug": drug_name,
        "event": signal.get("event", "Unknown event"),
        "event_title": event_title,
        "medical_context": llm_output.get("medical_context", ""),
        "statistical_justification": llm_output.get("statistical_justification", ""),
        "trend_analysis": llm_output.get("trend_analysis", ""),
        "literature_references": llm_output.get("literature_references", []),
        "priority": llm_output.get("priority", "UNKNOWN"),
        "next_steps": llm_output.get("next_steps", ""),
        "raw_trend": signal.get("trend", {})
    }

def generate_signal_packet_payloads(signals_json: dict[str, Any]) -> list[dict[str, Any]]:
    signals = signals_json.get("signals") or []
    top_signals = signals[:3]
    return [build_signal_packet_data(signals_json, signal_index=index) for index in range(len(top_signals))]