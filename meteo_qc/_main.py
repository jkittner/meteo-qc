from __future__ import annotations

from collections import defaultdict
from typing import TypedDict

import pandas as pd

from meteo_qc._data import FUNCS
from meteo_qc._data import Result


class FinalResult(TypedDict):
    columns: dict[str, dict[str, Result]]


column_mapping: dict[str, list[str]] = defaultdict(lambda: ['generic'])


def apply_qc(df: pd.DataFrame) -> FinalResult:
    final_res: FinalResult = {'columns': defaultdict(dict)}
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(
            f'the pandas.DataFrame index must be of type pandas.DatetimeIndex,'
            f' not {type(df.index)}',
        )
    # sort the data by the DateTimeIndex
    df_sorted = df.sort_index()
    for column in df_sorted.columns:
        qc_types = column_mapping[column]
        for qc_type in qc_types:
            funcs = FUNCS[qc_type]
            for f in funcs:
                final_res['columns'][column][f.__name__] = f(df_sorted[column])

    return final_res
