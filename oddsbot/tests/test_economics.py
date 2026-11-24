import math

import pytest

from oddsbot.config import load_config
from oddsbot.economics import (breakeven_win_rate, expected_value, fee, full_kelly,
                               kelly_stake, net_loss, net_win, wilson_lower_bound)


def test_fee_and_pnl_match_spec_at_180():
    assert fee(10, 1.80) == pytest.approx(0.26667, abs=1e-4)
    assert net_win(10, 1.80) == pytest.approx(7.7333, abs=1e-4)
    assert net_loss(10, 1.80) == pytest.approx(-10.2667, abs=1e-4)


def test_breakeven_180():
    be = breakeven_win_rate(1.80)
    assert be == pytest.approx(0.570370, abs=1e-6)  # 57.04%
    assert expected_value(be, 1.80) == pytest.approx(0.0, abs=1e-12)


def test_breakeven_closed_form():
    # L/(W+L) = (1+fee)/payout
    for payout in (1.5, 1.8, 1.9, 2.0):
        f = 0.06 * (1 - 1 / payout)
        assert breakeven_win_rate(payout) == pytest.approx((1 + f) / payout)


def test_kelly_zero_at_or_below_breakeven():
    be = breakeven_win_rate(1.80)
    assert full_kelly(be, 1.80) == pytest.approx(0.0, abs=1e-12)
    assert full_kelly(0.5, 1.80) == 0.0


def test_kelly_is_growth_optimal():
    p, payout = 0.62, 1.80
    w, l = net_win(1, payout), -net_loss(1, payout)
    g = lambda f: p * math.log(1 + f * w) + (1 - p) * math.log(1 - f * l)
    fk = full_kelly(p, payout)
    assert fk > 0
    assert g(fk) > g(fk * 0.9) and g(fk) > g(fk * 1.1)


def test_kelly_stake_cap_min_and_rounding():
    d = kelly_stake(1000, 1.80, p=0.70, kelly_fraction=0.5, max_stake_pct=0.02)
    assert d.capped and d.stake == 20.0
    d = kelly_stake(1000, 1.80, p=0.575, kelly_fraction=0.5, max_stake_pct=0.02)
    assert not d.capped and 0 < d.stake < 20 and round(d.stake, 2) == d.stake
    d = kelly_stake(50, 1.80, p=0.575, kelly_fraction=0.5, min_stake=1.0)
    assert d.stake == 0.0 and "minimum" in d.reason
    d = kelly_stake(1000, 1.80, p=0.55)
    assert d.stake == 0.0 and "no edge" in d.reason


def test_lower_bound_shrinks_small_samples():
    # 58% over 300 trades is NOT statistically above 57.04% -> no stake
    d = kelly_stake(1000, 1.80, wins=174, n=300, use_lower_bound=True)
    assert d.stake == 0.0
    assert wilson_lower_bound(174, 300) < breakeven_win_rate(1.80)


def test_config_loads():
    cfg = load_config()
    assert cfg["contract"]["payout"] == 1.80
    assert cfg["contract"]["draw_is_loss"] is True
