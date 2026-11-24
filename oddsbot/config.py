"""Loads the single config file (config.toml). Python 3.11+ (stdlib tomllib)."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parent / "config.toml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    with open(path or DEFAULT_PATH, "rb") as fh:
        cfg = tomllib.load(fh)
    c = cfg["contract"]
    if not c["payout"] > 1.0:
        raise ValueError("payout must be > 1.0")
    if not 0.0 <= c["fee_rate"] < 1.0:
        raise ValueError("fee_rate must be in [0, 1)")
    if not c.get("draw_is_loss", True):
        raise ValueError("draw_is_loss must stay true: the contract counts a draw as a loss")
    s = cfg["sizing"]
    if not 0.0 < s["kelly_fraction"] <= 1.0:
        raise ValueError("kelly_fraction must be in (0, 1]")
    if not 0.0 < s["max_stake_pct"] <= 1.0:
        raise ValueError("max_stake_pct must be in (0, 1]")
    return cfg
