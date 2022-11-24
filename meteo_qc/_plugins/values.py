from __future__ import annotations

from datetime import timedelta

import pandas as pd

from meteo_qc._data import register
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


def _has_spikes_or_dip(
        s: pd.Series[float],
        delta: float,
) -> tuple[bool, pd.DataFrame]:
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
    return bool(df['flag'].any()), df[df['flag'] == True]  # noqa: E712


def _is_persistent(
        s: pd.Series[float],
        window: int,
) -> tuple[bool, pd.DataFrame]:
    df = s.to_frame()
    df['flag'] = False
    if len(df) <= window:
        return False, df[df['flag'] == True]  # noqa: E712

    # pandas rolling sucks pretty hard, therefore we need to implement our own
    left = 0
    right = window
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
    return bool(df['flag'].any()), df[df['flag'] == True]  # noqa: E712


@register('temperature', lower_bound=-40, upper_bound=50)
@register('dew_point', lower_bound=-60, upper_bound=50)
@register('relhum', lower_bound=10, upper_bound=100)
@register('windspeed', lower_bound=0, upper_bound=30)
@register('winddirection', lower_bound=0, upper_bound=360)
@register('pressure', lower_bound=860, upper_bound=1055)
def range_check(
        s: pd.Series[float],
        lower_bound: float,
        upper_bound: float,
) -> Result:
    df = s.to_frame()
    df['flag'] = False
    df['flag'] = (
        df.iloc[:, 0].lt(lower_bound) |
        df.iloc[:, 0].gt(upper_bound)
    )

    if df.index.name is None:
        date_name = 'index'
    else:
        date_name = df.index.name

    df = df.reset_index()
    # we need something json serializable
    df[date_name] = df[date_name].astype(int)
    # replace NaNs with NULLs, since json tokenizing can't handle them
    df = df.replace([float('nan')], [None])
    result = bool(df['flag'].any())
    if result is True:
        return Result(
            function=range_check.__name__,
            passed=False,
            msg=f'out of allowed range of [{lower_bound} - {upper_bound}]',
            data=df[df['flag'] == True].values.tolist(),  # noqa: E712
        )
    else:
        return Result(function=range_check.__name__, passed=True)


@register('temperature', delta=0.3)
@register('dew_point', delta=0.3)
@register('relhum', delta=1)
@register('pressure', delta=0.5)
def spike_dip_check(s: pd.Series[float], delta: float) -> Result:
    assert isinstance(s.index, pd.DatetimeIndex)
    freqstr = s.index.freqstr
    if freqstr is None:
        freqstr = infer_freq(s)
        if freqstr is None:
            return Result(
                function=spike_dip_check.__name__,
                passed=False,
                msg='cannot determine temporal resolution frequency',
            )

    freq_delta = pd.to_timedelta(freqstr)
    _delta = (freq_delta.total_seconds() / 60) * delta
    # reindex if values are missing
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq=freqstr)
    s = s.reindex(full_idx)
    result, df = _has_spikes_or_dip(s, delta=_delta)

    if df.index.name is None:
        date_name = 'index'
    else:
        date_name = df.index.name

    df = df.reset_index()
    # we need something json serializable
    df[date_name] = df[date_name].astype(int)
    # replace NaNs with NULLs, since json tokenizing can't handle them
    df = df.replace([float('nan')], [None])
    if result is True:
        return Result(
            function=spike_dip_check.__name__,
            passed=False,
            msg=(
                f'spikes or dips detected. Exceeded allowed delta of '
                f'{delta} / min'
            ),
            data=df.values.tolist(),
        )
    else:
        return Result(function=spike_dip_check.__name__, passed=True)


@register('temperature', window=timedelta(hours=3))
@register('dew_point', window=timedelta(hours=3))
@register('windspeed', window=timedelta(hours=5))
@register('relhum', window=timedelta(hours=5))
@register('global_radiation', window=timedelta(minutes=20))
@register('pressure', window=timedelta(hours=6))
def persistence_check(s: pd.Series[float], window: timedelta) -> Result:
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
    result, df = _is_persistent(s, window=timestamps_per_interval)

    if df.index.name is None:
        date_name = 'index'
    else:
        date_name = df.index.name

    df = df.reset_index()
    # we need something json serializable
    df[date_name] = df[date_name].astype(int)
    # replace NaNs with NULLs, since json tokenizing can't handle them
    df = df.replace([float('nan')], [None])
    if result is True:
        return Result(
            function=persistence_check.__name__,
            passed=False,
            msg=f'some values are the same for longer than {window}',
            data=df.values.tolist(),
        )
    else:
        return Result(function=persistence_check.__name__, passed=True)
