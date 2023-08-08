from __future__ import annotations

from typing import Any

import pandas as pd

from meteo_qc._plugins.values import infer_freq
from meteo_qc._plugins.values import PluginBase
from meteo_qc._plugins.values import register
from meteo_qc._plugins.values import Result


@register('generic')
class MissingTimestamps(PluginBase):
    def common_checks(self) -> pd.DataFrame:
        assert isinstance(self.s.index, pd.DatetimeIndex)
        self.freq = infer_freq(self.s)
        if self.freq is None:
            raise ValueError('cannot determine temporal resolution frequency')

        df = self.s.to_frame()
        if df.index.name is None:
            self.date_name = 'index'
        else:
            self.date_name = df.index.name

        self.full_idx = pd.date_range(
            df.index.min(),
            df.index.max(),
            freq=self.freq,
            name=self.date_name,
        )
        return df

    def as_df(
            self,
            s: pd.Series[float],
            *args: Any,
            **kwargs: Any,
    ) -> pd.DataFrame:
        df = self.common_checks()
        df_full = pd.DataFrame(
            index=self.full_idx, columns=pd.MultiIndex.from_tuples(
                [
                    (s.index.name, 'value'),
                    (s.index.name, self.name),
                ],
            ),
        )
        df_full.loc[df.index, (s.index.name, 'value')] = df.index.values
        df_full.loc[
            df.index, (s.index.name, self.name),
        ] = df_full[s.index.name]['value'].isnull()
        return df_full

    def as_result(
            self,
            s: pd.Series[float],
            *args: Any,
            **kwargs: Any,
    ) -> Result:
        df = self.common_checks()
        nr_missing = len(self.full_idx) - len(s.index)
        # get the rows that were missing
        timestamps_missing = self.full_idx.difference(s.index)

        df = df.reindex(self.full_idx).loc[timestamps_missing].reset_index()
        # timestamp to milliseconds
        df[self.date_name] = df[self.date_name].astype(int) // 1000000
        # replace NaNs with NULLs, since json tokenizing can't handle them
        df = df.replace([float('nan')], [None])
        if nr_missing > 0:
            return Result(
                function=self.name,
                passed=False,
                msg=(
                    f'missing {nr_missing} timestamps '
                    f'(assumed frequency: {self.freq})'
                ),
                data=df.values.tolist(),
            )
        else:
            return Result(function=self.name, passed=True)


@register('generic')
class NullValues(PluginBase):
    def common_checks(self) -> pd.DataFrame:
        df = pd.DataFrame(
            index=self.s.index, columns=pd.MultiIndex.from_tuples(
                [
                    (self.s.name, 'value'),
                    (self.s.name, self.name),
                ],
            ),
        )
        # make mypy happy...
        assert isinstance(self.s.name, str)
        df.loc[:, (self.s.name, 'value')] = self.s.values
        df.loc[:, (self.s.name, self.name)] = self.s.isnull()
        self.null_vals = sum(df[self.s.name][self.name])

        if df.index.name is None:
            self.date_name = 'index'
        else:
            self.date_name = df.index.name

        return df

    def as_df(
            self,
            s: pd.Series[float],
            *args: Any,
            **kwargs: Any,
    ) -> pd.DataFrame:
        return self.common_checks()

    def as_result(
            self,
            s: pd.Series[float],
            *args: Any,
            **kwargs: Any,
    ) -> Result:
        df = self.common_checks().reset_index()
        # timestamp to milliseconds
        df[self.date_name] = df[self.date_name].astype(int) // 1000000
        # replace NaNs with NULLs, since json tokenizing can't handle them
        df = df.replace([float('nan')], [None])
        df.columns = df.columns.droplevel()
        df.rename(columns={'value': s.name}, inplace=True)
        if self.null_vals > 0:
            return Result(
                function=self.name,
                passed=False,
                msg=f'found {self.null_vals} values that are null',
                data=df[df[self.name] == True].values.tolist(),  # noqa: E712
            )
        else:
            return Result(function=self.name, passed=True)
