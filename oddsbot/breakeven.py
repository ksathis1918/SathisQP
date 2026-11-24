"""Part 1 CLI — break-even calculator and half-Kelly sizing table.

    python -m oddsbot.breakeven                 # uses config.toml
    python -m oddsbot.breakeven --payout 1.85   # override payout
    python -m oddsbot.breakeven --stake 10
"""
from __future__ import annotations

import argparse

from .config import load_config
from .economics import (breakeven_win_rate, expected_value, fee, full_kelly,
                        kelly_stake, net_loss, net_win)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--payout", type=float)
    ap.add_argument("--stake", type=float, default=10.0)
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    c, s = cfg["contract"], cfg["sizing"]
    payout = args.payout or c["payout"]
    fr = c["fee_rate"]
    st = args.stake

    be = breakeven_win_rate(payout, fr)
    print(f"Contract: {c['broker']}  payout {payout:.2f}x  fee_rate {fr}  expiry {c['expiry_minutes']}m (draw = loss)")
    print(f"Per ${st:.2f} stake: fee ${fee(st, payout, fr):.4f}   win {net_win(st, payout, fr):+.4f}   "
          f"loss {net_loss(st, payout, fr):+.4f}")
    print(f"After-fee BREAK-EVEN win rate: {be * 100:.4f}%")
    print(f"(Without fees it would be {100 / payout:.4f}%; fees add {(be - 1 / payout) * 100:.4f} pp.)\n")

    bank = s["bankroll"]
    print(f"Sizing on bankroll ${bank:,.2f}: {s['kelly_fraction']:.2f}x Kelly, cap {s['max_stake_pct'] * 100:.1f}%, "
          f"min stake ${s['min_stake']}")
    print(f"{'win rate':>9} {'EV/$1':>9} {'full K':>8} {'frac K':>8} {'stake':>9}  note")
    for p in (0.55, be, 0.575, 0.58, 0.60, 0.62, 0.65, 0.70):
        fk = full_kelly(p, payout, fr)
        d = kelly_stake(bank, payout, fr, p=p, kelly_fraction=s["kelly_fraction"],
                        max_stake_pct=s["max_stake_pct"], min_stake=s["min_stake"],
                        stake_step=s["stake_step"])
        note = "cap" if d.capped else ("" if d.reason == "ok" else d.reason.split(":")[0])
        print(f"{p * 100:8.2f}% {expected_value(p, payout, fr):+9.4f} {fk * 100:7.2f}% "
              f"{fk * s['kelly_fraction'] * 100:7.2f}% {d.stake:9.2f}  {note}")

    print("\nTrack-record sizing (Wilson 95% lower bound, the default in config):")
    for wins, n in ((180, 300), (348, 600), (1200, 2000)):
        d = kelly_stake(bank, payout, fr, wins=wins, n=n, kelly_fraction=s["kelly_fraction"],
                        max_stake_pct=s["max_stake_pct"], min_stake=s["min_stake"],
                        stake_step=s["stake_step"], use_lower_bound=True, z=s["confidence_z"])
        print(f"  {wins}/{n} = {wins / n * 100:.2f}% observed -> lower bound {d.p_used * 100:.2f}% "
              f"-> stake ${d.stake:.2f} ({d.reason})")


if __name__ == "__main__":
    main()
