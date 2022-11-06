[![ci](https://github.com/theendlessriver13/meteo-qc/actions/workflows/ci.yaml/badge.svg)](https://github.com/theendlessriver13/meteo-qc/actions/workflows/ci.yaml)
[![docs](https://github.com/theendlessriver13/meteo-qc/actions/workflows/docs.yaml/badge.svg)](https://github.com/theendlessriver13/meteo-qc/actions/workflows/docs.yaml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/theendlessriver13/meteo-qc/main.svg)](https://results.pre-commit.ci/latest/github/theendlessriver13/meteo-qc/main)

# meteo-qc

quality control meteorological data in a `pandas.DataFrame`.


### Anforderungen

- Spaltenweise Kontrolle
- Pro Spalte mehrere Tests
- Sinnvolle default Argumente
- Argumente von Plugins müssen anpassbar sein
- Argumente müssen spaltenweise anpassbar sein
    - Das kann aber auch so sein:
    ```python
    from meteo_qc._plugins import range_check

    @register('custom thingy')
    def modified(s):
        return range_check(s, arg1, arg2)
    ```
