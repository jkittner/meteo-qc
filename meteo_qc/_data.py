from __future__ import annotations

import pkgutil
from collections import defaultdict
from typing import Callable
from typing import NamedTuple
from typing import TYPE_CHECKING

import pandas as pd

from meteo_qc import _plugins


class Result(NamedTuple):
    function: str
    passed: bool
    msg: str | None = None


if TYPE_CHECKING:
    FUNC_T = Callable[[pd.Series[float]], Result]

FUNCS: dict[str, list[FUNC_T]] = defaultdict(list)


def register(t: str) -> Callable[[FUNC_T], FUNC_T]:
    def register_decorator(func: FUNC_T) -> FUNC_T:
        FUNCS[t].append(func)
        return func
    return register_decorator


def _import_plugins() -> None:
    # https://github.com/asottile/pyupgrade/blob/5c27928ee21db3e6ffa62bae714c6c74a9ad208d/pyupgrade/_data.py#L119
    plugins_path = _plugins.__path__
    mod_infos = pkgutil.walk_packages(plugins_path, f'{_plugins.__name__}.')
    for _, name, _ in mod_infos:
        __import__(name, fromlist=['_trash'])


_import_plugins()
