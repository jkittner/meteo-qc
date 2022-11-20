from __future__ import annotations

import pandas as pd

from meteo_qc._data import register
from meteo_qc._data import Result
from meteo_qc.checks import infer_freq


@register('generic')
def missing_timestamps(s: pd.Series[float]) -> Result:
    assert isinstance(s.index, pd.DatetimeIndex)
    freq = infer_freq(s)
    if freq is None:
        return Result(
            function=missing_timestamps.__name__,
            passed=False,
            msg='cannot determine temporal resolution frequency',
        )
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq=freq)

    nr_missing = len(full_idx) - len(s.index)
    if nr_missing > 0:
        return Result(
            function=missing_timestamps.__name__,
            passed=False,
            msg=(
                f'missing {nr_missing} timestamps (assumed frequency: {freq})'
            ),
        )
    else:
        return Result(function=missing_timestamps.__name__, passed=True)


@register('generic')
def null_values(s: pd.Series[float]) -> Result:
    null_vals = sum(s.isnull())
    if null_vals > 0:
        return Result(
            function=null_values.__name__,
            passed=False,
            msg=f'found {null_vals} values that are null',
        )
    else:
        return Result(function=null_values.__name__, passed=True)
