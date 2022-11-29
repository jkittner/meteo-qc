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
    """
    Final Result dictionary of the quality control.

    :param columns: column that were quality controlled, mapping to a
        dictionary of ``results`` being another dictionary mapping the check
        function to to its Result.
    :param passed: did the the entire quality control pass (all checks)
    :param data_start_date: timestamp in milliseconds of the **start** date of
        the provided input data
    :param data_end_date: timestamp in milliseconds of the **end** date of the
        provided input data.
    """
    columns: dict[str, ColumnResult]
    passed: bool
    data_start_date: int
    data_end_date: int


def apply_qc(df: pd.DataFrame, column_mapping: ColumnMapping) -> FinalResult:
    """
    Apply the quality control to a a ``pandas.DataFrame``.

    :param df: The DataFrame the quality control should be applied to
    :param column_mapping: A column mapping (:func:`meteo_qc.ColumnMapping`),
        that assigns groups to columns. See :func:`meteo_qc.ColumnMapping` for
        more information on how to create and customize one.

    :returns: A result as json serializable dictionary to be rendered in a
        an HTML template.

        .. code-block:: python

            {
                "columns": {
                    {
                        "temp": {
                            "passed": False,
                            "results": {
                                "missing_timestamps": Result(
                                    function="missing_timestamps",
                                    passed=False,
                                    msg="missing 1 timestamps (assumed frequency: 10T)",
                                    data=None,
                                ),
                                "null_values": Result(
                                    function="null_values",
                                    passed=False,
                                    msg="found 7 values that are null",
                                    data=[
                                        [16410348000000, None, True],
                                        [16410384000000, None, True],
                                        [16410420000000, None, True],
                                        [16410456000000, None, True],
                                        [16410492000000, None, True],
                                        [16410528000000, None, True],
                                        [16410564000000, None, True],
                                    ],
                                ),
                                "persistence_check": Result(
                                    function="persistence_check", passed=True, msg=None, data=None
                                ),
                                "range_check": Result(
                                    function="range_check", passed=True, msg=None, data=None
                                ),
                                "spike_dip_check": Result(
                                    function="spike_dip_check", passed=True, msg=None, data=None
                                ),
                            },
                        },
                    },
                    ...
                },
                "data_end_date": 16410564000000,
                "data_start_date": 16410312000000,
                "passed": False,
            }
    """  # noqa: E501
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
