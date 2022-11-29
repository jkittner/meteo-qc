from __future__ import annotations

from typing import Iterator

import pandas as pd

from meteo_qc._data import FUNCS


class GroupList:
    def __init__(self, lst: list[str] | None = None) -> None:
        if lst is not None:
            self._lst = lst
        else:
            self._lst = ['generic']

    def __iter__(self) -> Iterator[str]:
        yield from self._lst

    def __contains__(self, v: str) -> bool:
        return v in self._lst

    def __eq__(self, __o: object) -> bool:
        return __o == self._lst

    def add_group(self, v: str) -> None:
        if v in FUNCS:
            self._lst.append(v)
        else:
            raise KeyError(f'unregistered group: {v!r}')

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self._lst})'


class ColumnMapping:
    """Class for adding columns of a dataframe to to groups. This can be done
    by calling:

    .. code-block:: python

        from meteo_qc import ColumnMapping

        column_mapping = ColumnMapping()
        column_mapping['temperature_2m'].add_group('temperature')

    which will add the column ``temperature_2m`` to the group
    ``temperature`` and run all checks registered for this group.
    """

    def __init__(self) -> None:
        self._dct: dict[str, GroupList] = {}

    def __getitem__(self, k: str) -> GroupList:
        item = self._dct.get(k)
        if item is not None:
            return item
        else:
            self._dct[k] = GroupList()
            return self._dct[k]

    @classmethod
    def autodetect_from_df(cls, df: pd.DataFrame) -> ColumnMapping:
        """Autodetect the groups from the column names.

        .. code-block:: python

            import meteo_qc
            import pandas as pd

            df = pd.DataFrame(
                data=[[10], [20]],
                index=pd.date_range(
                    start='2022-01-01 10:00',
                    end='2022-01-01 10:10',
                    freq='10T',
                ),
                columns=['air_temperature_2m'],
            )

            column_mapping = meteo_qc.ColumnMapping().autodetect_from_df(df)
            print(column_mapping)

        This will result in the ``air_temperature_2m`` column being registered
        with the temperature group.

        .. code-block:: console

            ColumnMapping({'air_temperature_2m': GroupList(['generic', 'temperature'])})

        :param df: The ``pandas.DataFrame`` to infer the groups from the column
            names

        :returns: An instance of :func:`meteo_qc.ColumnMapping` with columns
            registered that could be inferred from the column name.
        :rtype: :func:`meteo_qc.ColumnMapping`
        """  # noqa: E501
        c = cls()
        groups = FUNCS
        for column in df.columns:
            for group in groups:
                if group in column:
                    c[column].add_group(group)
        return c

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self._dct})'
