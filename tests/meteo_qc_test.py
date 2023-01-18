from datetime import timedelta
from datetime import timezone

import pandas as pd
import pytest

from meteo_qc import apply_qc
from meteo_qc import ColumnMapping
from meteo_qc import get_plugin_args
from meteo_qc import persistence_check
from meteo_qc import register
from meteo_qc import Result


@pytest.fixture(scope='session')
def data():
    data = pd.read_csv('testing/test_data.csv')
    data['date'] = pd.to_datetime(data['date'], utc=True)
    return data.set_index('date')


def test_invalid_dataframe_index():
    df = pd.DataFrame(data=[[10, 20], [10, 20]])
    column_mapping = ColumnMapping()
    with pytest.raises(TypeError) as exc_info:
        apply_qc(df, column_mapping)

    msg, = exc_info.value.args
    assert msg == (
        'the pandas.DataFrame index must be of type pandas.DatetimeIndex, '
        "not <class 'pandas.core.indexes.range.RangeIndex'>"
    )


def test_invalid_dataframe_index_not_timezone_aware():
    df = pd.DataFrame(
        data=[[10, 20], [10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:20',
            freq='10T',
        ),
        columns=['a', 'b'],
    )
    column_mapping = ColumnMapping()
    with pytest.raises(TypeError) as exc_info:
        apply_qc(df, column_mapping)

    msg, = exc_info.value.args
    assert msg == 'the pandas.DataFrame index must be timezone aware'


@pytest.mark.parametrize(
    'tz',
    ('UTC', timezone.utc, 'Etc/GMT-1', 'Europe/Berlin'),
)
def test_generic_good_data_check_different_tz_definitions(tz):
    df = pd.DataFrame(
        data=[[10, 20], [10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:20',
            freq='10T',
            tz=tz,
        ),
        columns=['a', 'b'],
    )
    column_mapping = ColumnMapping()
    results = apply_qc(df, column_mapping)['columns']['a']['results']
    assert results['missing_timestamps'].passed is True
    assert results['missing_timestamps'].msg is None


@pytest.mark.parametrize(
    ('tz', 'start', 'end'),
    (
        ('UTC', 1641031200000, 1641031800000),
        ('Etc/GMT-1', 1641027600000, 1641028200000),
        ('Europe/Berlin', 1641027600000, 1641028200000),
        ('America/Los_Angeles', 1641060000000, 1641060600000),
    ),
)
def test_timestamps_are_always_in_utc(tz, start, end):
    df = pd.DataFrame(
        data=[[10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:10',
            freq='10T',
            tz=tz,
        ),
        columns=['a', 'b'],
    )
    column_mapping = ColumnMapping()
    results = apply_qc(df, column_mapping)
    # check timestamps of data_start_date and data_end_date
    assert results['data_start_date'] == start
    assert results['data_end_date'] == end


def test_generic_missing_timestamp_data_too_short():
    df = pd.DataFrame(
        data=[[10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:10',
            freq='10T',
            tz='UTC',
        ),
        columns=['a', 'b'],
    )
    column_mapping = ColumnMapping()
    results = apply_qc(df, column_mapping)
    # check timestamps of data_start_date and data_end_date
    assert results['data_start_date'] == 1641031200000
    assert results['data_end_date'] == 1641031800000
    results_cols = results['columns']
    assert results_cols['a']['results']['missing_timestamps'].passed is False
    assert results_cols['a']['results']['missing_timestamps'].msg == (
        'cannot determine temporal resolution frequency'
    )
    assert results_cols['b']['results']['missing_timestamps'].passed is False
    assert results_cols['b']['results']['missing_timestamps'].msg == (
        'cannot determine temporal resolution frequency'
    )


def test_generic_checks_are_applied_as_default(data):
    column_mapping = ColumnMapping()
    results = apply_qc(data, column_mapping)
    for col in results['columns']:
        assert set(results['columns'][col]['results'].keys()) == {
            'missing_timestamps', 'null_values',
        }
        assert results['columns'][col]['passed'] is False
    pressure_res = results['columns']['pressure_reduced']['results']
    temp_res = results['columns']['temp']['results']
    sunshine_res = results['columns']['sunshine_duration']['results']

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
    assert pressure_res['null_values'].msg == 'found 7 values that are null'
    assert temp_res['null_values'].passed is False
    assert temp_res['null_values'].function == 'null_values'
    assert temp_res['null_values'].msg == 'found 7 values that are null'
    assert sunshine_res['null_values'].passed is True


def test_changed_column_mapping_pressure_checks(data):
    column_mapping = ColumnMapping()
    column_mapping['pressure_reduced'].add_group('pressure')
    column_mapping['pressure'].add_group('pressure')
    column_mapping['pressure_persistent'].add_group('pressure')
    results = apply_qc(data, column_mapping)['columns']
    pressure_red_range = results['pressure_reduced']['results']['range_check']
    pressure_range = results['pressure']['results']['range_check']
    pressure_spike = results['pressure']['results']['spike_dip_check']

    assert pressure_red_range.passed is False
    assert pressure_red_range.function == 'range_check'
    assert pressure_red_range.msg == 'out of allowed range of [860 - 1055]'
    assert pressure_range.passed is True
    assert pressure_range.msg is None
    # spike ro dip
    assert pressure_spike.passed is False
    assert pressure_spike.msg == (
        'spikes or dips detected. Exceeded allowed delta of 0.3 / min'
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

    column_mapping = ColumnMapping()
    results = apply_qc(data, column_mapping)['columns']
    pressure_result = results['pressure_reduced']['results']['over_1000']
    temp_result = results['temp']['results']['over_1000']

    assert pressure_result.passed is False
    assert pressure_result.function == 'over_1000'
    assert pressure_result.msg == 'over 1000!'

    assert temp_result.passed is True
    assert temp_result.function == 'over_1000'
    assert temp_result.msg is None


def test_changed_column_mapping_pressure_persistence_check(data):
    column_mapping = ColumnMapping()
    column_mapping['pressure_persistent'].add_group('pressure')
    results = apply_qc(data, column_mapping)['columns']
    persists = results['pressure_persistent']['results']['persistence_check']
    assert persists.passed is False
    assert persists.msg == 'some values are the same for longer than 6:00:00'
    assert persists.function == 'persistence_check'


def test_persistence_check_with_excludes(data):

    @register('custom', window=timedelta(hours=6), excludes=[10.0])
    def custom_check(s, window, excludes):
        return persistence_check(s=s, window=window, excludes=excludes)

    column_mapping = ColumnMapping()
    column_mapping['pressure_persistent'].add_group('custom')
    results = apply_qc(data, column_mapping)['columns']
    persists = results['pressure_persistent']['results']['custom_check']
    assert persists.passed is True
    assert persists.msg is None
    assert persists.function == 'persistence_check'


def test_changed_column_mapping_pressure_persistence_check_data_short():
    column_mapping = ColumnMapping()
    df = pd.DataFrame(
        data=[[10, 20], [10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:20',
            freq='10T',
            tz='UTC',
        ),
        columns=['a', 'b'],
    )
    column_mapping['a'].add_group('pressure')
    results = apply_qc(df, column_mapping)['columns']
    persists = results['a']['results']['persistence_check']
    assert persists.passed is True


def test_changed_column_mapping_pressure_persistence_check_no_freq():
    column_mapping = ColumnMapping()
    df = pd.DataFrame(
        data=[[10, 20], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:10',
            freq='10T',
            tz='UTC',
        ),
        columns=['a', 'b'],
    )
    assert isinstance(df.index, pd.DatetimeIndex)
    df.index.freq = None  # type: ignore [misc]
    column_mapping['a'].add_group('pressure')
    results = apply_qc(df, column_mapping)['columns']
    persists = results['a']['results']['persistence_check']
    assert persists.passed is False
    assert persists.function == 'persistence_check'
    assert persists.msg == 'cannot determine temporal resolution frequency'


def test_stacked_decorators_persistence(data):
    column_mapping = ColumnMapping()
    column_mapping['pressure_reduced'].add_group('pressure')
    column_mapping['temp'].add_group('temperature')
    results = apply_qc(data, column_mapping)['columns']
    persists_p = results['pressure_reduced']['results']['persistence_check']
    assert persists_p.passed is True
    assert persists_p.msg is None
    assert persists_p.function == 'persistence_check'
    assert results['pressure_reduced']['passed'] is False
    persists_t = results['temp']['results']['persistence_check']
    assert persists_t.passed is True
    assert persists_t.msg is None
    assert persists_t.function == 'persistence_check'
    assert results['temp']['passed'] is False


@pytest.mark.parametrize(
    ('tz', 'first_data'),
    (
        ('UTC', 1641031800000),
        ('Etc/GMT-1', 1641028200000),
        ('Europe/Berlin', 1641028200000),
        ('America/Los_Angeles', 1641060600000),
    ),
)
def test_timestamps_are_correct_in_data_all_utc(tz, first_data):
    df = pd.DataFrame(
        data=[[10, 20], [10, None], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:20',
            freq='10T',
            tz=tz,
        ),
        columns=['a', 'temp'],
    )
    column_mapping = ColumnMapping()
    results = apply_qc(df, column_mapping)['columns']
    data = results['temp']['results']['null_values'].data
    assert data is not None
    # first flagged data
    assert data[0][0] == first_data


def test_one_minute_data_freq_can_be_inferred():
    df = pd.DataFrame(
        data=[[10, 20], [10, None], [10, 20]],
        index=pd.date_range(
            start='2022-01-01 10:00',
            end='2022-01-01 10:02',
            freq='1T',
            tz='UTC',
        ),
        columns=['a', 'temp'],
    )
    df.index.freq = None  # type: ignore [attr-defined]
    column_mapping = ColumnMapping()
    column_mapping['temp'].add_group('temperature')

    results = apply_qc(df, column_mapping)['columns']
    data = results['temp']['results']['null_values'].data
    assert data is not None
    assert data[0][0] == 1641031260000


def test_get_plugin_args(data):
    args = get_plugin_args()
    # defaults are registered
    assert args['temperature']['range_check']['upper_bound'] == 50
    # can be changed
    args['temperature']['range_check']['upper_bound'] = 69
    assert args['temperature']['range_check']['upper_bound'] == 69
    # check newly set value is used
    column_mapping = ColumnMapping()
    column_mapping['temp'].add_group('temperature')
    result = apply_qc(df=data, column_mapping=column_mapping)
    assert result['columns']['temp']['results']['range_check'].passed is True
