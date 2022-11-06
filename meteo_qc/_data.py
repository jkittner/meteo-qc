from __future__ import annotations

import pkgutil
from collections import defaultdict
from typing import Any
from typing import Callable
from typing import NamedTuple
from typing import TYPE_CHECKING
from typing import TypedDict

from meteo_qc import _plugins


class Result(NamedTuple):
    function: str
    passed: bool
    msg: str | None = None
    data: list[list[float]] | None = None


if TYPE_CHECKING:
    # TODO: Callable[[pd.Series[float]], Result]
    FUNC_T = Any


class FunctionInfo(TypedDict):
    func: FUNC_T
    kwargs: dict[str, Any]


FUNCS: dict[str, list[FunctionInfo]] = defaultdict(list)


def register(t: str, **kwargs: Any) -> Callable[[FUNC_T], FUNC_T]:
    def register_decorator(func: FUNC_T) -> FUNC_T:
        func_info = FunctionInfo(func=func, kwargs=kwargs)
        FUNCS[t].append(func_info)
        return func
    return register_decorator


def _import_plugins() -> None:
    # https://github.com/asottile/pyupgrade/blob/5c27928ee21db3e6ffa62bae714c6c74a9ad208d/pyupgrade/_data.py#L119
    plugins_path = _plugins.__path__
    mod_infos = pkgutil.walk_packages(plugins_path, f'{_plugins.__name__}.')
    for _, name, _ in mod_infos:
        __import__(name, fromlist=['_trash'])


_import_plugins()
