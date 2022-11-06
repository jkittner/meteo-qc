from __future__ import annotations

import pandas as pd

from meteo_qc._data import register
from meteo_qc._data import Result
from meteo_qc.checks import has_spikes_or_dip
from meteo_qc.checks import out_of_bounds


@register('pressure')
def range_check(
        s: pd.Series[float],
        lower_bound: float = 700,
        upper_bound: float = 1080,
) -> Result:
    result = out_of_bounds(s, lower=lower_bound, upper=upper_bound)
    if result is True:
        return Result(
            function=range_check.__name__,
            passed=False,
            msg=(
                f'pressure out of allowed range of '
                f'[{lower_bound} - {upper_bound}]'
            ),
        )
    else:
        return Result(function=range_check.__name__, passed=True)


@register('pressure')
def spike_dip_check(s: pd.Series[float], delta: float = 5) -> Result:
    # TODO: make delta per minute to calculate the correct one here
    result = has_spikes_or_dip(s, delta=delta)
    if result is True:
        return Result(
            function=spike_dip_check.__name__,
            passed=False,
            msg=(
                f'spikes or dips detected. Exceeded allowed delta of {delta}'
            ),
        )
    else:
        return Result(function=spike_dip_check.__name__, passed=True)
