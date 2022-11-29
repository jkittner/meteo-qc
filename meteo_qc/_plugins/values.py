from __future__ import annotations

from datetime import timedelta

import pandas as pd

from meteo_qc._data import register
from meteo_qc._data import Result

pd.options.mode.chained_assignment = None  # type: ignore[assignment]


def infer_freq(s: pd.Series[float]) -> str | None:
    """Infer the frequency of a :func:`pd.DateTimeIndex` by copying the dates
        and shifting them by one timestamp then subtracting the dates from each
        other taking the minimum.

        :param s: a :func:`pd.Series` with a :func:`pd.DateTimeIndex`.

        :returns: if the series is too short (< 3) ``None`` since the frequency
            cannot be inferred. Else a ``freqstr`` e.g. ``10T``.
    """
    # pd.infer_freq is not working with values missing. Instead compute the
    # minimum frequency
    # shift the (sorted) index by one
    if len(s) < 3:
        return None
    idx_diff = s.index[1:] - s.index[:-1]
    offset = pd.tseries.frequencies.to_offset(idx_diff.min())
    freq = None
    if offset is not None:  # pragma no branch
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

    def _equals(x: pd.Series[float]) -> bool:
        if len(x) >= window:
            first_val = x.iloc[0]
            return bool((x == first_val).all())
        else:
            return False

    df['flag'] = df[s.name].rolling(
        window=window,
        min_periods=1,
        closed='right',
    ).apply(_equals).astype(bool)
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
    """
    A check function checking if values in the :func:`pd.Series` `s` are within
    a range.

    This function can be used to write your own custom range checks.

    :param s: the :func:`pd.Series` to be checked
    :param lower_bound: the lower bound of the allowed values (inclusive)
    :param upper_bound: the lower bound of the allowed values (inclusive)

    :returns: a :func:`meteo_qc.Result` object containing the outcome of the
        applied check.
    """
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
    # timestamp to milliseconds
    df[date_name] = df[date_name].astype(int) // 100000
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
@register('relhum', delta=4)
@register('pressure', delta=0.3)
def spike_dip_check(s: pd.Series[float], delta: float) -> Result:
    """
    A check function checking if values in the :func:`pd.Series` `s` have
    sudden spikes or dips.

    This function can be used to write your own custom spike dip checks.

    :param s: the :func:`pd.Series` to be checked
    :param delta: maximum allowed change per minute

    :returns: a :func:`meteo_qc.Result` object containing the outcome of the
        applied check.
    """
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
    else:  # pragma: no cover
        date_name = df.index.name

    df = df.reset_index()
    # we need something json serializable
    # timestamp to milliseconds
    df[date_name] = df[date_name].astype(int) // 100000
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


@register('temperature', window=timedelta(hours=2))
@register('dew_point', window=timedelta(hours=2))
@register('windspeed', window=timedelta(hours=5))
@register('relhum', window=timedelta(hours=5))
@register('pressure', window=timedelta(hours=6))
def persistence_check(s: pd.Series[float], window: timedelta) -> Result:
    """
    A check function checking if values in the :func:`pd.Series` ``s`` are
    persistent for a certain amount of time. "stuck values".

    This function can be used to write your own custom persistence checks.

    :param s: the :func:`pd.Series` to be checked
    :param window: a timedelta after which the values must have changed

    :returns: a :func:`meteo_qc.Result` object containing the outcome of the
        applied check.
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
    timestamps_per_interval = window // freq_delta

    # reindex if values are missing
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq=freqstr)
    s = s.reindex(full_idx)
    result, df = _is_persistent(s, window=timestamps_per_interval)

    if df.index.name is None:
        date_name = 'index'
    else:  # pragma: no cover
        date_name = df.index.name

    df = df.reset_index()
    # we need something json serializable
    # timestamp to milliseconds
    df[date_name] = df[date_name].astype(int) // 100000
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
