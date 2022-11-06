from __future__ import annotations

import pandas as pd

from meteo_qc._data import register
from meteo_qc._data import Result


@register('generic')
def missing_timestamps(s: pd.Series[float]) -> Result:
    assert isinstance(s.index, pd.DatetimeIndex)
    # pd.infer_freq is not working with values missing. Instead compute the
    # minimum frequency
    # shift the (sorted) index by one
    if len(s) < 3:
        freq = None
    else:
        idx_diff = s.index[1:] - s.index[:-1]
        offset = pd.tseries.frequencies.to_offset(idx_diff.min())
        freq = None
        if offset is not None:
            freq = offset.freqstr

    if freq is None:
        return Result(
            function=missing_timestamps.__name__,
            passed=False,
            msg='cannot determine temporal resolution frequency',
        )
    # https://github.com/pandas-dev/pandas-stubs/pull/430
    full_idx = pd.date_range(
        s.index.min(),
        s.index.max(),
        freq=freq,  # type: ignore[arg-type]
    )

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
