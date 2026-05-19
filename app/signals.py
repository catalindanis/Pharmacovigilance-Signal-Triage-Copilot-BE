from __future__ import annotations

from dataclasses import dataclass
from math import inf


@dataclass(frozen=True)
class SignalMetrics:
    event: str
    n_drug_event: int
    n_drug_total: int
    n_all_event: int
    n_all_total: int
    n_other_event: int
    n_other_total: int
    prr: float
    ror: float
    chi_square_yates: float
    serious_ratio: float
    frequency_ratio: float
    score: float
    valid_signal: bool


def calculate_prr(
    n_drug_event: int,
    n_drug_total: int,
    n_all_event: int,
    n_all_total: int,
) -> float:
    if n_drug_total <= 0 or n_all_total <= 0 or n_all_event <= 0:
        return 0.0
    return (n_drug_event / n_drug_total) / (n_all_event / n_all_total)


def calculate_ror(a: int, b: int, c: int, d: int) -> float:
    if b <= 0 or c <= 0:
        return inf if a > 0 and d > 0 else 0.0
    if a <= 0 or d <= 0:
        return 0.0
    return (a / b) / (c / d)


def calculate_yates_chi_square(a: int, b: int, c: int, d: int) -> float:
    n = a + b + c + d
    if n <= 0:
        return 0.0

    denominator = (a + b) * (c + d) * (a + c) * (b + d)
    if denominator <= 0:
        return 0.0

    corrected = abs(a * d - b * c) - (n / 2)
    if corrected < 0:
        corrected = 0.0

    return (n * corrected * corrected) / denominator


def is_valid_signal(prr: float, n_drug_event: int, chi_square_yates: float) -> bool:
    return prr >= 2.0 and n_drug_event >= 3 and chi_square_yates >= 4.0


def calculate_weighted_score(
    frequency_ratio: float,
    serious_ratio: float,
    frequency_weight: float = 0.6,
    seriousness_weight: float = 0.4,
) -> float:
    return (frequency_weight * frequency_ratio) + (seriousness_weight * serious_ratio)


def build_signal_metrics(
    drug_event_counts: dict[str, int],
    all_event_counts: dict[str, int],
    serious_event_counts: dict[str, int],
    n_drug_total: int,
    n_all_total: int,
) -> list[SignalMetrics]:
    metrics: list[SignalMetrics] = []

    n_other_total = max(n_all_total - n_drug_total, 0)

    for event, n_drug_event in drug_event_counts.items():
        n_all_event = all_event_counts.get(event, 0)
        if n_all_event <= 0:
            continue

        n_other_event = max(n_all_event - n_drug_event, 0)
        b = max(n_drug_total - n_drug_event, 0)
        d = max(n_other_total - n_other_event, 0)

        prr = calculate_prr(n_drug_event, n_drug_total, n_all_event, n_all_total)
        ror = calculate_ror(n_drug_event, b, n_other_event, d)
        chi_square_yates = calculate_yates_chi_square(n_drug_event, b, n_other_event, d)

        serious_count = serious_event_counts.get(event, 0)
        serious_ratio = (serious_count / n_drug_event) if n_drug_event > 0 else 0.0
        frequency_ratio = (n_drug_event / n_drug_total) if n_drug_total > 0 else 0.0
        score = calculate_weighted_score(frequency_ratio=frequency_ratio, serious_ratio=serious_ratio)

        metrics.append(
            SignalMetrics(
                event=event,
                n_drug_event=n_drug_event,
                n_drug_total=n_drug_total,
                n_all_event=n_all_event,
                n_all_total=n_all_total,
                n_other_event=n_other_event,
                n_other_total=n_other_total,
                prr=prr,
                ror=ror,
                chi_square_yates=chi_square_yates,
                serious_ratio=serious_ratio,
                frequency_ratio=frequency_ratio,
                score=score,
                valid_signal=is_valid_signal(prr, n_drug_event, chi_square_yates),
            )
        )

    metrics.sort(
        key=lambda m: (m.valid_signal, m.score, m.prr, m.n_drug_event),
        reverse=True,
    )
    return metrics
