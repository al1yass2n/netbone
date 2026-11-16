from __future__ import annotations

import pytest

from netbone.methods._utils import binomial_upper_tail


def test_binomial_upper_tail_handles_almost_certain_large_tail() -> None:
    assert binomial_upper_tail(
        observed=1,
        trials=10_000,
        probability=0.25,
        inclusive=False,
    ) == pytest.approx(1.0)


def test_binomial_upper_tail_matches_small_hand_computable_values() -> None:
    assert binomial_upper_tail(
        observed=3,
        trials=5,
        probability=0.5,
        inclusive=True,
    ) == pytest.approx(0.5)
    assert binomial_upper_tail(
        observed=1,
        trials=5,
        probability=0.5,
        inclusive=False,
    ) == pytest.approx(0.8125)
