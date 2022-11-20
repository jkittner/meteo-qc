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
        c = cls()
        groups = FUNCS
        for column in df.columns:
            for group in groups:
                if group in column:
                    c[column].add_group(group)
        return c

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self._dct})'
