from __future__ import annotations

from collections import defaultdict
from typing import TypedDict

import pandas as pd

from meteo_qc._colum_mapping import ColumnMapping
from meteo_qc._data import FUNCS
from meteo_qc._data import Result


class ColumnResult(TypedDict):
    results: dict[str, Result]
    passed: bool


class FinalResult(TypedDict):
    columns: dict[str, ColumnResult]
    passed: bool
    data_start_date: int
    data_end_date: int


def apply_qc(df: pd.DataFrame, column_mapping: ColumnMapping) -> FinalResult:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(
            f'the pandas.DataFrame index must be of type pandas.DatetimeIndex,'
            f' not {type(df.index)}',
        )
    final_res: FinalResult = {
        'columns': defaultdict(
            lambda: {'results': {}, 'passed': False},
        ),
        'passed': False,
        'data_start_date': int(df.index.min().timestamp() * 10000),
        'data_end_date': int(df.index.max().timestamp() * 10000),
    }
    # sort the data by the DateTimeIndex
    df_sorted = df.sort_index()
    for column in df_sorted.columns:
        # all groups associated with this column
        qc_types = column_mapping[column]
        final_res_col = final_res['columns'][column]
        for qc_type in qc_types:
            # all functions registered for this group
            registerd_funcs = FUNCS[qc_type]
            for func in registerd_funcs:
                call_result = func['func'](df_sorted[column], **func['kwargs'])
                final_res_col['results'][func['func'].__name__] = call_result
        # check if entire column passed
        final_res_col['passed'] = all(
            [i.passed for i in final_res_col['results'].values()],
        )
    # check if the entire QC failed
    final_res['passed'] = all(
        [i['passed'] for i in final_res['columns'].values()],
    )

    return final_res
