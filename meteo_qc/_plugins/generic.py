from __future__ import annotations

import pandas as pd

from meteo_qc._data import register
from meteo_qc._data import Result
from meteo_qc._plugins.values import infer_freq


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

    df = s.to_frame()
    if df.index.name is None:
        date_name = 'index'
    else:
        date_name = df.index.name

    full_idx = pd.date_range(
        df.index.min(),
        df.index.max(),
        freq=freq,
        name=date_name,
    )

    nr_missing = len(full_idx) - len(s.index)
    # get the rows that were missing
    timestamps_missing = full_idx.difference(s.index)

    df = df.reindex(full_idx).loc[timestamps_missing].reset_index()
    # timestamp to milliseconds
    df[date_name] = df[date_name].astype(int) // 1000000
    # replace NaNs with NULLs, since json tokenizing can't handle them
    df = df.replace([float('nan')], [None])
    if nr_missing > 0:
        return Result(
            function=missing_timestamps.__name__,
            passed=False,
            msg=(
                f'missing {nr_missing} timestamps (assumed frequency: {freq})'
            ),
            data=df.values.tolist(),
        )
    else:
        return Result(function=missing_timestamps.__name__, passed=True)


@register('generic')
def null_values(s: pd.Series[float]) -> Result:
    df = s.to_frame()
    df['flag'] = s.isnull()
    null_vals = sum(df['flag'])

    if df.index.name is None:
        date_name = 'index'
    else:
        date_name = df.index.name

    df = df.reset_index()
    # timestamp to milliseconds
    df[date_name] = df[date_name].astype(int) // 1000000
    # replace NaNs with NULLs, since json tokenizing can't handle them
    df = df.replace([float('nan')], [None])
    if null_vals > 0:
        return Result(
            function=null_values.__name__,
            passed=False,
            msg=f'found {null_vals} values that are null',
            data=df[df['flag'] == True].values.tolist(),  # noqa: E712
        )
    else:
        return Result(function=null_values.__name__, passed=True)
