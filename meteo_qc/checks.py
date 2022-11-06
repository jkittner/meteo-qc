from __future__ import annotations

import pandas as pd


def out_of_bounds(s: pd.Series[float], lower: float, upper: float) -> bool:
    return bool(s.min() < lower or s.max() > upper)


def has_spikes_or_dip(s: pd.Series[float], delta: float) -> bool:
    df = s.to_frame()

    def _compare(s: pd.Series[float]) -> bool:
        if len(s) == 1:
            return False
        return bool(abs(s[0] - s[1]) > delta)

    df['flag'] = df.rolling(
        window=2,
        min_periods=1,
        closed='right',
    ).apply(_compare).astype(bool)
    # TODO: also return where, and make sure the spike or dip is labelled
    # correctly
    return bool(df['flag'].any())
