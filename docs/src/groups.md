# Groups

A few common groups are preregistered and can be used directly

## generic

The `generic` group is preregistered and automatically applied to every column.
It contains two checks.

### `missing_timestamps`

Checks if timestamps are missing. This check is applied to all columns.

### `null_values`

Checks if values are `NULL`. This check is applied to all columns.

## `temperature`

A group for temperature related checks.

### `range_check`

Checking if values are in a range from `-40` to `50`.

### `spike_dip_check`

Checking if the parameter has spikes or dips that exceed `0.3` per minute.

### `persistence_check`

Checking if values are the same for longer than `2` hours.

## `dew_point`

Group for dew point related checks.

### `range_check`

Checking if values are in a range from `-60` to `50`.

### `spike_dip_check`

Checking if the parameter has spikes or dips that exceed `0.3` per minute.

### `persistence_check`

Checking if values are the same for longer than `2` hours.

## `windspeed`

Group for wind speed related checks.

### `range_check`

Checking if values are in a range from `0` to `30`.

### `persistence_check`

Checking if values are the same for longer than `5` hours.

## `winddirection`

Group for wind direction related checks.

### `range_check`

Checking if values are in a range from `0` to `36`.

### `persistence_check`

## `relhum`

Group for relative humidity related checks.

### `range_check`

Checking if values are in a range from `10` to `100`.

### `spike_dip_check`

Checking if the parameter has spikes or dips that exceed `4` per minute.

### `persistence_check`

Checking if values are the same for longer than `5` hours.

## `pressure`

Group for pressure related checks.

### `range_check`

Checking if values are in a range from `860` to `1055`.

### `spike_dip_check`

Checking if the parameter has spikes or dips that exceed `0.3` per minute.

### `persistence_check`

Checking if values are the same for longer than `6` hours.
