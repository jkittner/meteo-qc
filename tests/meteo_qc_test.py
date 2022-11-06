import pandas as pd
import pytest

from meteo_qc import apply_qc
from meteo_qc import column_mapping
from meteo_qc import register
from meteo_qc import Result


@pytest.fixture(scope='session')
def data():
    return pd.read_csv(
        'testing/test_data.csv',
        index_col='date',
        parse_dates=True,
    )


def test_invalid_dataframe_index():
    df = pd.DataFrame(data=[[10, 20], [10, 20]])
    with pytest.raises(TypeError) as exc_info:
        apply_qc(df)

    msg, = exc_info.value.args
    assert msg == (
        'the pandas.DataFrame index must be of type pandas.DatetimeIndex, '
        "not <class 'pandas.core.indexes.range.RangeIndex'>"
    )


def test_generic_good_data():
    df = pd.DataFrame(
        data=[[10, 20], [10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:20',
            freq='10T',
        ),
        columns=['a', 'b'],
    )
    results = apply_qc(df)
    assert results['columns']['a']['missing_timestamps'].passed is True
    assert results['columns']['a']['missing_timestamps'].msg is None


def test_generic_missing_timestamp_data_too_short():
    df = pd.DataFrame(
        data=[[10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:10',
            freq='10T',
        ),
        columns=['a', 'b'],
    )
    results = apply_qc(df)
    assert results['columns']['a']['missing_timestamps'].passed is False
    assert results['columns']['a']['missing_timestamps'].msg == (
        'cannot determine temporal resolution frequency'
    )
    assert results['columns']['b']['missing_timestamps'].passed is False
    assert results['columns']['b']['missing_timestamps'].msg == (
        'cannot determine temporal resolution frequency'
    )


def test_generic_checks_are_applied_as_default(data):
    results = apply_qc(data)
    for col in results['columns']:
        assert set(results['columns'][col].keys()) == {
            'missing_timestamps', 'null_values',
        }
    pressure_res = results['columns']['pressure_reduced']
    temp_res = results['columns']['temp']
    sunshine_res = results['columns']['sunshine_duration']

    # missing timestamps are listed
    assert pressure_res['missing_timestamps'].passed is False
    assert pressure_res['missing_timestamps'].function == 'missing_timestamps'
    assert pressure_res['missing_timestamps'].msg == (
        'missing 1 timestamps (assumed frequency: 10T)'
    )
    assert temp_res['missing_timestamps'].passed is False
    assert temp_res['missing_timestamps'].function == 'missing_timestamps'
    assert temp_res['missing_timestamps'].msg == (
        'missing 1 timestamps (assumed frequency: 10T)'
    )
    # null values are detected
    assert pressure_res['null_values'].passed is False
    assert pressure_res['null_values'].function == 'null_values'
    assert pressure_res['null_values'].msg == 'found 1 values that are null'
    assert temp_res['null_values'].passed is False
    assert temp_res['null_values'].function == 'null_values'
    assert temp_res['null_values'].msg == 'found 1 values that are null'
    assert sunshine_res['null_values'].passed is True


def test_changed_column_mapping_pressure_checks(data):
    column_mapping['pressure_reduced'].append('pressure')
    column_mapping['pressure'].append('pressure')
    results = apply_qc(data)
    pressure_red_range = results['columns']['pressure_reduced']['range_check']
    pressure_range = results['columns']['pressure']['range_check']
    pressure_spike = results['columns']['pressure']['spike_dip_check']

    assert pressure_red_range.passed is False
    assert pressure_red_range.function == 'range_check'
    assert pressure_red_range.msg == (
        'pressure out of allowed range of [700 - 1080]'
    )
    assert pressure_range.passed is True
    assert pressure_range.msg is None
    # spike ro dip
    assert pressure_spike.passed is False
    assert pressure_spike.msg == (
        'spikes or dips detected. Exceeded allowed delta of 5'
    )


def test_can_register_new_check(data):
    @register('generic')
    def over_1000(s):
        ret = bool(s.max() > 1000)
        if ret is True:
            return Result(
                over_1000.__name__,
                passed=False,
                msg='over 1000!',
            )
        else:
            return Result(over_1000.__name__, passed=True)

    results = apply_qc(data)
    pressure_result = results['columns']['pressure_reduced']['over_1000']
    temp_result = results['columns']['temp']['over_1000']

    assert pressure_result.passed is False
    assert pressure_result.function == 'over_1000'
    assert pressure_result.msg == 'over 1000!'

    assert temp_result.passed is True
    assert temp_result.function == 'over_1000'
    assert temp_result.msg is None
