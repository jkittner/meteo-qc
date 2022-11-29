from __future__ import annotations

import pkgutil
from collections import defaultdict
from typing import Any
from typing import Callable
from typing import NamedTuple
from typing import TypedDict

from meteo_qc import _plugins


class Result(NamedTuple):
    """
    A ``NamedTuple`` storing the Results of one quality check.

    :param function: the name of the function that applied the check
    :param passed: did the check pass?
    :param msg: message returned from the check e.g. a specific error/problem
    :param data: the data that did not pass the check
    """
    function: str
    passed: bool
    msg: str | None = None
    data: list[list[float]] | None = None


# TODO: this needs the series and variable number of kwargs
FUNC_T = Callable[..., Result]


class FunctionInfo(TypedDict):
    func: FUNC_T
    kwargs: dict[str, Any]


FUNCS: dict[str, list[FunctionInfo]] = defaultdict(list)


def get_plugin_args() -> dict[str, dict[str, dict[str, Any]]]:
    """
    Get the (default) arguments that were registered with the check functions.
    For example when using this:

    .. code-block:: python

        import meteo_qc
        import pandas as pd

        @meteo_qc.register('custom_group', arg=123)
        def custom_check(s: pd.Series, arg: int) -> meteo_qc.Result:
            ...

        print(meteo_qc.get_plugin_args())

    For ``custom_group`` the argument ``arg`` was registered with ``123``.

    .. code-block:: python

        {
            ...
            'generic': {'missing_timestamps': {}, 'null_values': {}},
            'custom_group': {'custom_check': {'arg': 123}},
            ...
        }

    This can also be used to change the default values e.g. for the group
    ``temperature``:

    .. code-block:: python

        import meteo_qc

        plugin_args = meteo_qc.get_plugin_args()
        plugin_args['temperature']['range_check']['lower_bound'] = -60

    :returns: A dictionary mapping the groups to a dictionary of registered
        check functions which will have a dictionary of the arguments
        registered as default for this function.
    """
    args = {}
    for group in FUNCS:
        args[group] = {i['func'].__name__: i['kwargs'] for i in FUNCS[group]}
    return args


def register(group: str, **kwargs: Any) -> Callable[[FUNC_T], FUNC_T]:
    """
    A decorator for registering a plugin function.

    .. code-block:: python

        import meteo_qc


        @meteo_qc.register('temperature', args1=5, pi=3.141)
        def custom_check(s: pd.DataFrame, arg1: int, pi: float) -> meteo_qc.Result:
            ...

    The function ``custom_check`` will now be called for every column that is
    registered with the group ``temperature`` and will be part of the
    :func:`meteo_qc.FinalResult` returned by :func:`meteo_qc.apply_qc`.

    The :func:`meteo_qc.register` decorators can also be stacked to register a
    function for multiple groups.

    .. code-block:: python

        import meteo_qc

        @meteo_qc.register('relhum', args1=10, pi=3.141)
        @meteo_qc.register('temperature', args1=5, pi=3.141)
        def custom_check(s: pd.DataFrame, arg1: int, pi: float) -> meteo_qc.Result:
            ...

    The function ``custom_check`` will now be called for every column that is
    registered with the group ``temperature`` **or** the group ``relhum``,
    but with the corresponding arguments. The assigned arguments can be checked
    using :func:`meteo_qc.get_plugin_args`.

    :param group: The group the function should registered with. This can be
        existing groups or a new group.

    :param kwargs: The keyword arguments that are associated with function that
        is decorated. For an example see above.
    """  # noqa: E501
    def register_decorator(func: FUNC_T) -> FUNC_T:
        func_info = FunctionInfo(func=func, kwargs=kwargs)
        FUNCS[group].append(func_info)
        return func
    return register_decorator


def _import_plugins() -> None:
    # https://github.com/asottile/pyupgrade/blob/5c27928ee21db3e6ffa62bae714c6c74a9ad208d/pyupgrade/_data.py#L119
    plugins_path = _plugins.__path__
    mod_infos = pkgutil.walk_packages(plugins_path, f'{_plugins.__name__}.')
    for _, name, _ in mod_infos:
        __import__(name, fromlist=['_trash'])


_import_plugins()
