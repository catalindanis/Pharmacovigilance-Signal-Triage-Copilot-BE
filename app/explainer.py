from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = PROJECT_ROOT / ".env"


SYSTEM_PROMPT = """
You are an expert Pharmacovigilance (PV) Data Scientist and Medical Reviewer.
Your task is to analyze a JSON payload containing statistical disproportionate reporting signals (PRR, ROR) for a specific drug.

For each signal, generate a "Signal Evidence Packet" consisting of:
1. Medical Context: Briefly explain the adverse event and its potential severity.
2. Statistical Justification: Explain why this was flagged as a signal using the provided PRR, ROR, and Yates' Chi-Square scores. Explain what these numbers mean in simple terms.
3. Trend Analysis: Mention if the signal is emerging or stable based on the trend data.
4. Recommendation: Suggest the next steps for the safety team (e.g., deeper medical review, label update consideration).

Output the response in a professional, clinical tone, formatted in Markdown.
""".strip()


@dataclass(frozen=True)
class SignalEvidencePacket:
    drug: str
    event: str
    markdown: str


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _resolve_llm_config(api_key: str | None = None, model: str | None = None) -> tuple[str, str]:
    env_file_values = _load_env_file(DOTENV_PATH)

    resolved_api_key = (
        api_key
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or env_file_values.get("GOOGLE_API_KEY")
        or env_file_values.get("GEMINI_API_KEY")
    )
    if not resolved_api_key:
        raise ValueError("GOOGLE_API_KEY is required to use the Gemini explainer")

    resolved_model = (
        model
        or os.getenv("PV_LLM_MODEL")
        or env_file_values.get("PV_LLM_MODEL")
        or DEFAULT_GEMINI_MODEL
    )
    return resolved_api_key, resolved_model


def _format_event_title(event: str) -> str:
    return event.strip().upper() if event else "UNKNOWN EVENT"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_ratio(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, str):
        return value
    if value == float("inf"):
        return "inf"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _priority_and_recommendation(signal: dict[str, Any]) -> tuple[str, str]:
    prr = float(signal.get("prr", 0) or 0)
    chi_square = float(signal.get("chi_square_yates", 0) or 0)
    serious_ratio = float(signal.get("serious_ratio", 0) or 0)
    emerging = bool(signal.get("trend", {}).get("emerging", False))

    if prr >= 10 or chi_square >= 50 or serious_ratio >= 0.8 or emerging:
        return (
            "HIGH",
            "Given the strong disproportionality, seriousness, and/or emerging trend, an expedited in-depth case-series review is recommended. Assess causality, clinical course, concomitant medications, and whether product labeling or risk communication should be updated.",
        )
    if prr >= 4 or chi_square >= 10 or serious_ratio >= 0.5:
        return (
            "MEDIUM",
            "A focused medical review of the reported cases is recommended. Confirm the clinical context, severity, and consistency with the known safety profile, and continue close monitoring for additional reports.",
        )
    return (
        "LOW",
        "Continue routine surveillance and monitor for additional accumulation of cases. A brief review should confirm whether the event is clinically plausible and consistent with the known profile.",
    )


def _medical_context(signal: dict[str, Any], drug_name: str) -> str:
    event_name = signal.get("event", "Unknown event")
    serious_ratio = float(signal.get("serious_ratio", 0) or 0)
    serious_text = "All reported cases (100%) were considered serious." if serious_ratio >= 0.999 else f"The serious ratio for this event was {_format_percent(serious_ratio)}."
    return (
        f"{event_name} is a clinically relevant adverse event that warrants review in the context of {drug_name}. "
        f"{serious_text}"
    )


def _statistical_justification(signal: dict[str, Any]) -> str:
    prr = _format_ratio(signal.get("prr"))
    ror = _format_ratio(signal.get("ror"))
    chi_square = _format_ratio(signal.get("chi_square_yates"))
    n_cases = signal.get("n_drug_event", 0)
    n_total = signal.get("n_drug_total", 0)

    return (
        f"The observed Proportional Reporting Ratio (PRR) of {prr} and Reporting Odds Ratio (ROR) of {ror} indicate that "
        f"this event is reported disproportionately more often with the drug compared with the background database. "
        f"The Yates' Chi-Square value of {chi_square} supports a statistically significant association. "
        f"There were {n_cases} cases reported out of {n_total} drug reports."
    )


def _trend_analysis(signal: dict[str, Any]) -> str:
    trend = signal.get("trend") or {}
    latest_month = trend.get("latest_month", "unknown")
    latest_count = trend.get("latest_count", 0)
    baseline_average = trend.get("baseline_average", 0.0)
    growth_ratio = trend.get("growth_ratio", "unknown")
    emerging = bool(trend.get("emerging", False))

    status = "emerging" if emerging else "stable"
    if growth_ratio == "inf":
        growth_text = "infinite due to a zero or near-zero baseline"
    else:
        growth_text = f"{growth_ratio}"

    return (
        f"The signal for {signal.get('event', 'Unknown event')} appears {status}. "
        f"The latest month ({latest_month}) recorded {latest_count} case(s), compared with a baseline average of {baseline_average} case(s) per month, "
        f"resulting in a growth ratio of {growth_text}."
    )


def _literature_references(signal: dict[str, Any]) -> list[str]:
    refs = signal.get("literature_refs") or signal.get("pubmed_refs") or []
    cleaned = [str(ref).strip() for ref in refs if str(ref).strip()]
    return cleaned


def _render_packet(signals_json: dict[str, Any], signal: dict[str, Any], signal_index: int) -> str:
    drug_name = signals_json.get("drug", "Unknown drug")
    event_title = _format_event_title(signal.get("event", "Unknown event"))
    priority, recommendation = _priority_and_recommendation(signal)
    references = _literature_references(signal)

    lines = [
        f"### Signal {signal_index + 1}: {event_title}",
        "",
        "#### 1. Medical Context",
        _medical_context(signal, drug_name),
        "",
        "#### 2. Statistical Justification",
        _statistical_justification(signal),
        "",
        "#### 3. Trend Analysis",
        _trend_analysis(signal),
        "",
        "#### 4. Literature References",
    ]

    if references:
        lines.extend(f"- {ref}" for ref in references)
    else:
        lines.append("No specific literature references were found in PubMed for this drug-event pair at this time.")

    lines.extend(
        [
            "",
            "#### 5. Priority & Recommendation",
            f"**Priority**: {priority}",
            f"**Next Steps**: {recommendation}",
        ]
    )
    return "\n".join(lines).strip()


def build_signal_packet_data(signals_json: dict[str, Any], signal_index: int = 0) -> dict[str, Any]:
    signals = signals_json.get("signals") or []
    if signal_index < 0 or signal_index >= len(signals):
        raise IndexError("signal_index is out of range for the provided payload")

    signal = signals[signal_index]
    drug_name = signals_json.get("drug", "Unknown drug")
    event_title = _format_event_title(signal.get("event", "Unknown event"))
    priority, recommendation = _priority_and_recommendation(signal)
    references = _literature_references(signal)

    medical_context = _medical_context(signal, drug_name)
    statistical_justification = _statistical_justification(signal)
    trend_analysis = _trend_analysis(signal)
    markdown = _render_packet(signals_json, signal, signal_index=signal_index)

    return {
        "signal_index": signal_index,
        "drug": drug_name,
        "event": signal.get("event", "Unknown event"),
        "event_title": event_title,
        "medical_context": medical_context,
        "statistical_justification": statistical_justification,
        "trend_analysis": trend_analysis,
        "literature_references": references,
        "priority": priority,
        "next_steps": recommendation,
        "markdown": markdown,
    }


def _trend_summary(trend: dict[str, Any] | None) -> str:
    if not trend:
        return "No trend data was provided."

    latest_month = trend.get("latest_month") or "unknown"
    latest_count = trend.get("latest_count", 0)
    baseline_average = trend.get("baseline_average", 0.0)
    growth_ratio = trend.get("growth_ratio")
    emerging = trend.get("emerging", False)

    growth_text = str(growth_ratio) if growth_ratio is not None else "unknown"

    status = "emerging" if emerging else "stable"
    return (
        f"Latest month: {latest_month}; latest count: {latest_count}; "
        f"baseline average: {baseline_average}; growth ratio: {growth_text}; signal status: {status}."
    )


def _build_user_prompt(signals_json: dict[str, Any], signal: dict[str, Any]) -> str:
    drug_name = signals_json.get("drug", "Unknown drug")
    return f"""
Please analyze the following signal for the drug {drug_name}.

Event: {signal.get('event', 'Unknown event')}
Drug Cases: {signal.get('n_drug_event', 0)}
Drug Total: {signal.get('n_drug_total', 0)}
All Event Cases: {signal.get('n_all_event', 0)}
All Total: {signal.get('n_all_total', 0)}
PRR: {signal.get('prr', 0)}
ROR: {signal.get('ror', 0)}
Chi-Square: {signal.get('chi_square_yates', 0)}
Serious Ratio: {signal.get('serious_ratio', 0)}
Frequency Ratio: {signal.get('frequency_ratio', 0)}
Score: {signal.get('score', 0)}
Valid Signal: {signal.get('valid_signal', False)}
Trend: {_trend_summary(signal.get('trend'))}

Write the answer as a clinically styled Markdown packet with the four requested sections.
""".strip()


def build_signal_packet_prompt(signals_json: dict[str, Any], signal_index: int = 0) -> tuple[str, str]:
    signals = signals_json.get("signals") or []
    if signal_index < 0 or signal_index >= len(signals):
        raise IndexError("signal_index is out of range for the provided payload")

    signal = signals[signal_index]
    return signal.get("event", "Unknown event"), _build_user_prompt(signals_json, signal)


def _extract_text_from_gemini_response(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        texts = [part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text")]
        if texts:
            return "\n".join(texts).strip()
    raise ValueError("Gemini response did not contain any text content")


class GeminiSignalExplainer:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key, self.model = _resolve_llm_config(api_key=api_key, model=model)
        self.session = None

    def generate_packet(self, signals_json: dict[str, Any], signal_index: int = 0) -> SignalEvidencePacket:
        signals = signals_json.get("signals") or []
        if signal_index < 0 or signal_index >= len(signals):
            raise IndexError("signal_index is out of range for the provided payload")

        signal = signals[signal_index]
        event_name = signal.get("event", "Unknown event")
        drug_name = signals_json.get("drug", "Unknown drug")
        markdown = _render_packet(signals_json, signal, signal_index=signal_index)
        return SignalEvidencePacket(drug=drug_name, event=event_name, markdown=markdown)


def generate_signal_packets(
    signals_json: dict[str, Any],
    api_key: str | None = None,
    model: str | None = None,
) -> list[SignalEvidencePacket]:
    signals = signals_json.get("signals") or []
    if not signals:
        return []

    resolved_api_key, resolved_model = _resolve_llm_config(api_key=api_key, model=model)
    explainer = GeminiSignalExplainer(api_key=resolved_api_key, model=resolved_model)
    packets: list[SignalEvidencePacket] = []
    for index in range(len(signals)):
        packets.append(explainer.generate_packet(signals_json, signal_index=index))
    return packets


def generate_signal_packet_payloads(signals_json: dict[str, Any]) -> list[dict[str, Any]]:
    signals = signals_json.get("signals") or []
    return [build_signal_packet_data(signals_json, signal_index=index) for index in range(len(signals))]


def generate_signal_packet(
    signals_json: dict[str, Any],
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    packets = generate_signal_packets(signals_json, api_key=api_key, model=model)
    if not packets:
        return "No valid signals found to analyze."

    first_packet = packets[0]
    return first_packet.markdown
