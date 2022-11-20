from __future__ import annotations

from datetime import timedelta

import pandas as pd

from meteo_qc._data import Result

pd.options.mode.chained_assignment = None  # type: ignore[assignment]


def infer_freq(s: pd.Series[float]) -> str | None:
    # pd.infer_freq is not working with values missing. Instead compute the
    # minimum frequency
    # shift the (sorted) index by one
    if len(s) < 3:
        return None
    idx_diff = s.index[1:] - s.index[:-1]
    offset = pd.tseries.frequencies.to_offset(idx_diff.min())
    freq = None
    if offset is not None:
        freq = offset.freqstr
    # https://github.com/pandas-dev/pandas-stubs/pull/430
    return freq  # type: ignore[return-value]


def _has_spikes_or_dip(s: pd.Series[float], delta: float) -> bool:
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


def _is_persistent(s: pd.Series[float], window: int) -> bool:
    df = s.to_frame()
    if len(df) <= window:
        return False

    # pandas rolling sucks pretty hard, therefore we need to implement our own
    left = 0
    right = window
    df['flag'] = False
    while right <= len(df):
        df_window = df.iloc[left:right]
        # check if first value is the same as all other values
        first_val = df_window.iloc[0, 0]
        df_window['equals'] = df_window.iloc[:, 0] == first_val
        if df_window['equals'].sum() == window:
            df['flag'].iloc[left:right] = True

        right += 1
        left += 1

    # TODO: also return where, and make sure the spike or dip is labelled
    # correctly
    return bool(df['flag'].any())


def range_check(
        s: pd.Series[float],
        lower_bound: float,
        upper_bound: float,
) -> Result:
    result = bool(s.min() < lower_bound or s.max() > upper_bound)
    if result is True:
        return Result(
            function=range_check.__name__,
            passed=False,
            msg=f'out of allowed range of [{lower_bound} - {upper_bound}]',
        )
    else:
        return Result(function=range_check.__name__, passed=True)


def spike_dip_check(s: pd.Series[float], delta: float) -> Result:
    """
    :param delta: allowed deviation per minute according to DWD
    """
    assert isinstance(s.index, pd.DatetimeIndex)
    freqstr = s.index.freqstr
    if freqstr is None:
        freqstr = infer_freq(s)
        if freqstr is None:
            return Result(
                function=persistence_check.__name__,
                passed=False,
                msg='cannot determine temporal resolution frequency',
            )

    freq_delta = pd.to_timedelta(freqstr)
    _delta = (freq_delta.total_seconds() / 60) * delta
    # reindex if values are missing
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq=freqstr)
    s = s.reindex(full_idx)
    result = _has_spikes_or_dip(s, delta=_delta)
    if result is True:
        return Result(
            function=spike_dip_check.__name__,
            passed=False,
            msg=(
                f'spikes or dips detected. Exceeded allowed delta of '
                f'{delta} / min'
            ),
        )
    else:
        return Result(function=spike_dip_check.__name__, passed=True)


def persistence_check(
        s: pd.Series[float],
        window: timedelta,
) -> Result:
    assert isinstance(s.index, pd.DatetimeIndex)
    freqstr = s.index.freqstr
    if freqstr is None:
        freqstr = infer_freq(s)
        if freqstr is None:
            return Result(
                function=persistence_check.__name__,
                passed=False,
                msg='cannot determine temporal resolution frequency',
            )

    freq_delta = pd.to_timedelta(freqstr)
    timestamps_per_interval = window // freq_delta

    # reindex if values are missing
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq=freqstr)
    s = s.reindex(full_idx)
    result = _is_persistent(s, window=timestamps_per_interval)
    if result is True:
        return Result(
            function=persistence_check.__name__,
            passed=False,
            msg=f'some values are the same for longer than {window}',
        )
    else:
        return Result(function=persistence_check.__name__, passed=True)
