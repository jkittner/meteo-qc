from __future__ import annotations

from datetime import timedelta

import pandas as pd

from meteo_qc._data import register
from meteo_qc._data import Result
from meteo_qc.checks import persistence_check
from meteo_qc.checks import range_check
from meteo_qc.checks import spike_dip_check


@register('pressure')
def range(
        s: pd.Series[float],
        lower_bound: float = 860,
        upper_bound: float = 1055,
) -> Result:
    return range_check(s, lower_bound=lower_bound, upper_bound=upper_bound)


@register('pressure')
def spike_dip(
        s: pd.Series[float],
        delta: float = 0.3,
) -> Result:
    return spike_dip_check(s, delta=delta)


@register('pressure')
def persistence(
        s: pd.Series[float],
        window: timedelta = timedelta(hours=6),
) -> Result:
    return persistence_check(s, window=window)
