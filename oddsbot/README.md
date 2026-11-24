# oddsbot — 15-minute crypto Up/Down research → paper trading

Runs locally on Python 3.11+. All settings live in `oddsbot/config.toml`. It places **no real orders**.

## Part 1 — Break-even and sizing
```
python -m oddsbot.breakeven            # break-even + half-Kelly table from config.toml
python -m oddsbot.breakeven --payout 1.85
python -m pytest -q oddsbot/tests
```
* Fee = stake × fee_rate × (1 − 1/payout). A win nets (payout − 1 − fee) × stake. A loss or a draw costs (1 + fee) × stake.
* Break-even p* = (1 + fee) / payout, which is **57.037%** at 1.80x.
* Kelly f* = (p·W − q·L)/(W·L), using net-of-fee W and L. The stake is kelly_fraction × f*, capped at max_stake_pct and floored to the broker minimum.
* By default, sizing uses the Wilson 95% lower bound of the observed win rate, not the raw estimate.
