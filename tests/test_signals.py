from app.signals import (
    build_signal_metrics,
    calculate_prr,
    calculate_ror,
    calculate_yates_chi_square,
    is_valid_signal,
)


def test_calculate_prr_basic() -> None:
    prr = calculate_prr(n_drug_event=10, n_drug_total=100, n_all_event=50, n_all_total=1000)
    assert round(prr, 4) == 2.0


def test_calculate_ror_handles_infinite() -> None:
    ror = calculate_ror(a=5, b=10, c=0, d=100)
    assert ror > 1e9


def test_yates_chi_square_positive_for_association() -> None:
    chi2 = calculate_yates_chi_square(a=12, b=88, c=18, d=882)
    assert chi2 > 4.0


def test_valid_signal_rule() -> None:
    assert is_valid_signal(prr=2.0, n_drug_event=3, chi_square_yates=4.0) is True
    assert is_valid_signal(prr=1.9, n_drug_event=3, chi_square_yates=4.0) is False


def test_build_signal_metrics_orders_valid_first() -> None:
    drug_event_counts = {
        "RENAL FAILURE ACUTE": 8,
        "RASH": 4,
    }
    all_event_counts = {
        "RENAL FAILURE ACUTE": 20,
        "RASH": 150,
    }
    serious_event_counts = {
        "RENAL FAILURE ACUTE": 6,
        "RASH": 0,
    }

    metrics = build_signal_metrics(
        drug_event_counts=drug_event_counts,
        all_event_counts=all_event_counts,
        serious_event_counts=serious_event_counts,
        n_drug_total=100,
        n_all_total=5000,
    )

    assert len(metrics) == 2
    assert metrics[0].event == "RENAL FAILURE ACUTE"
    assert metrics[0].score >= metrics[1].score
