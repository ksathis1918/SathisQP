"""Part 1 — contract economics: fees, break-even win rate, expected value, fractional Kelly.

All amounts are per unit of allocation (stake) unless a stake is passed in.

Contract (hard facts):
    win  -> receive payout * stake back            gross profit = (payout - 1) * stake
    loss -> lose the full stake (a draw is a loss)
    fee  =  stake * fee_rate * (1 - 1/payout), charged on every trade, win or lose

So per $1 staked:
    W = (payout - 1) - fee_per_unit        net gain on a win
    L = 1 + fee_per_unit                   net loss on a loss
    break-even p* = L / (W + L)
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def fee(stake: float, payout: float, fee_rate: float = 0.06) -> float:
    """Broker fee for one trade: stake * fee_rate * (1 - 1/payout)."""
    if payout <= 1.0:
        raise ValueError("payout must be > 1.0")
    return stake * fee_rate * (1.0 - 1.0 / payout)


def net_win(stake: float, payout: float, fee_rate: float = 0.06) -> float:
    """Net P&L of a winning trade (positive)."""
    return (payout - 1.0) * stake - fee(stake, payout, fee_rate)


def net_loss(stake: float, payout: float, fee_rate: float = 0.06) -> float:
    """Net P&L of a losing trade (negative). Draws are losses."""
    return -stake - fee(stake, payout, fee_rate)


def trade_pnl(won: bool, stake: float, payout: float, fee_rate: float = 0.06) -> float:
    return net_win(stake, payout, fee_rate) if won else net_loss(stake, payout, fee_rate)


def breakeven_win_rate(payout: float, fee_rate: float = 0.06) -> float:
    """After-fee win rate at which expected P&L is exactly zero."""
    w = net_win(1.0, payout, fee_rate)
    l = -net_loss(1.0, payout, fee_rate)
    if w <= 0:
        return 1.0  # can never break even
    return l / (w + l)


def expected_value(p: float, payout: float, fee_rate: float = 0.06) -> float:
    """Expected net P&L per $1 staked at win rate p."""
    return p * net_win(1.0, payout, fee_rate) + (1.0 - p) * net_loss(1.0, payout, fee_rate)


def full_kelly(p: float, payout: float, fee_rate: float = 0.06) -> float:
    """Growth-optimal fraction of bankroll to stake, net of fees.

    Maximises  p*ln(1 + f*W) + (1-p)*ln(1 - f*L)  =>  f* = (p*W - (1-p)*L) / (W*L).
    Returns 0 when there is no edge (never a negative / "bet the other side" value,
    because the opposite direction is a different contract with its own fee).
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0, 1]")
    w = net_win(1.0, payout, fee_rate)
    l = -net_loss(1.0, payout, fee_rate)
    if w <= 0:
        return 0.0
    f = (p * w - (1.0 - p) * l) / (w * l)
    # f*L < 1 always holds for p < 1, but clamp so a loss can never exceed bankroll.
    return max(0.0, min(f, 1.0 / l))


def wilson_lower_bound(wins: int, n: int, z: float = 1.96) -> float:
    """Lower bound of the Wilson score interval for a binomial win rate."""
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / denom)


@dataclass(frozen=True)
class StakeDecision:
    stake: float              # amount to allocate (0 = skip)
    p_used: float             # win rate the sizing was based on
    full_kelly_frac: float    # f* at p_used
    applied_frac: float       # fraction of bankroll actually staked
    capped: bool              # True if max_stake_pct bound
    reason: str


def kelly_stake(
    bankroll: float,
    payout: float,
    fee_rate: float = 0.06,
    *,
    p: float | None = None,
    wins: int | None = None,
    n: int | None = None,
    kelly_fraction: float = 0.5,
    max_stake_pct: float = 0.02,
    min_stake: float = 1.0,
    stake_step: float = 0.01,
    use_lower_bound: bool = True,
    z: float = 1.96,
) -> StakeDecision:
    """Fractional-Kelly stake with a hard cap and a broker minimum.

    Pass either `p` (a point win-rate estimate) or `wins` and `n` (a track record).
    With a track record and use_lower_bound=True, the Wilson lower bound is used,
    so a small or lucky sample is sized down automatically.
    """
    if bankroll <= 0:
        return StakeDecision(0.0, 0.0, 0.0, 0.0, False, "bankroll <= 0")
    if wins is not None and n is not None:
        p_used = wilson_lower_bound(wins, n, z) if use_lower_bound else (wins / n if n else 0.0)
    elif p is not None:
        p_used = p
    else:
        raise ValueError("pass p, or wins and n")

    be = breakeven_win_rate(payout, fee_rate)
    fk = full_kelly(p_used, payout, fee_rate)
    if fk <= 0:
        return StakeDecision(0.0, p_used, 0.0, 0.0, False,
                             f"no edge: p={p_used:.4f} <= break-even {be:.4f}")

    frac = fk * kelly_fraction
    capped = frac > max_stake_pct
    frac = min(frac, max_stake_pct)
    stake = math.floor(bankroll * frac / stake_step + 1e-9) * stake_step
    stake = round(stake, 8)
    if stake < min_stake:
        return StakeDecision(0.0, p_used, fk, 0.0, capped,
                             f"stake {bankroll * frac:.2f} below broker minimum {min_stake}")
    return StakeDecision(stake, p_used, fk, stake / bankroll, capped, "ok")
