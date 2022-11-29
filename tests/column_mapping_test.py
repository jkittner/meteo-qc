import pandas as pd
import pytest

from meteo_qc import ColumnMapping
from meteo_qc._colum_mapping import GroupList


def test_trying_to_add_unregistered_group():
    c = ColumnMapping()
    with pytest.raises(KeyError) as exc_info:
        assert 'unregistered' not in c['foo']
        c['foo'].add_group('unregistered')

    msg, = exc_info.value.args
    assert msg == "unregistered group: 'unregistered'"


def test_column_mapping_repr():
    c = ColumnMapping()
    c['foo'].add_group('pressure')
    r = repr(c)
    assert r == "ColumnMapping({'foo': GroupList(['generic', 'pressure'])})"


def test_column_mapping_autodetect_from_df():
    df = pd.DataFrame(
        data=[[10, 20], [10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:20',
            freq='10T',
        ),
        columns=['temp_mean', 'pressure_mean'],
    )
    c = ColumnMapping.autodetect_from_df(df)
    assert c['pressure_mean'] == GroupList(['generic', 'pressure'])
