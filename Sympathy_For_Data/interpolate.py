import os
import collections
import numpy as np
from scipy.interpolate import interp1d

from sympathy.api import adaf
from sympathy.api.exceptions import SyDataError, SyConfigurationError, sywarn
from cde_functions_new import RemoveETKC
from cde_functions_new import RenameCrankAngleRaster

spec_dir = "EvalCases"

def get_spec():
    file_list = []
    for root, dirs, files in os.walk(spec_dir):
        for file_ in files:
            file_path = os.path.join(root, file_)
            if file_path.endswith(".csv"):
                file_list.append(file_path)

    signal_names = []
    sample_rates = []
    basis_signals = []
    for file_ in file_list:
        with open(file_) as f:
            con = f.readlines()
            for line in con[1:]: #ignore the header line
                if line:
                    tmp = line.split(";")
                    if len(tmp) < 3:
                        continue
                    signal_name = tmp[0]
                    sample_rate = tmp[2]
                    if not signal_name in signal_names:
                        signal_names.append(signal_name)
                        sample_rates.append(sample_rate)

    # calculate basis_signal
    for i, sr in enumerate(sample_rates):
        if sr != "crank":
            sample_rates[i] = float(sr)
            basis_signals.append("")
        else:
            sample_rates[i] = np.NaN
            basis_signals.append("INCA/CRANK_ANGLE_INTERPOLATION_TARGET")

    return signal_names, sample_rates, basis_signals

def get_new_timebasis(in_adaffile, dt, signals):
    """
    Get new timebasis covering the same range as all the old timebases using
    step size dt.
    """
    if dt <= 0:
        raise SyConfigurationError('Time step must be positive.')

    t_start = np.inf
    t_end = -np.inf
    basis_kind = None
    basis_unit = None

    # The range of the new time basis should be the superset of all the
    # times in the resampled rasters.
    # TODO: What about reference times here?
    for signal_name in signals:
        if signal_name not in in_adaffile.ts.keys():
            sywarn("Missing signal: {}".format(signal_name))
            continue
        signal = in_adaffile.ts[signal_name]
        raster_name = signal.raster_name()
        system_name = signal.system_name()
        old_basis = in_adaffile.sys[system_name][raster_name].basis_column()
        basis = old_basis.value()
        unit = old_basis.attr.get_or_empty('unit')

        if basis_kind:
            if basis_kind != basis.dtype.kind:
                raise SyDataError(
                    "Either all rasters must be datetime type or "
                    "all rasters must be numeric.")
        else:
            basis_kind = basis.dtype.kind
        if basis_unit and unit and basis_unit != unit:
            raise SyDataError(
                "All selected signals must have the same time unit.")
        elif unit:
            basis_unit = unit

        t_start = min(t_start, basis[0])
        t_end = max(t_end, basis[-1])
    if t_end <= t_start:
        # None of the selected signals were present, return empty target basis
        return np.array([]), ''
    if basis_kind == 'M':
        dt *= np.timedelta64(1000000, 'us')
    timebasis_new = np.arange(t_start, t_end, dt)
    return timebasis_new, basis_unit

def get_raster_dict(adaffile):
    if adaffile.is_valid():
        return collections.OrderedDict(
            [('/'.join([system_name, raster_name]), (system_name, raster_name))
             for system_name, system in adaffile.sys.items()
             for raster_name in system.keys()])
    else:
        return {}

def resample_signal(origin_raster, new_raster, signal):
    """Resample signal to new timebasis."""
    interp_methods = ("nearest",
                      "nearest",
                      "linear")

    origin_basis = origin_raster.basis_column().value()
    new_basis = new_raster.basis_column().value()

    if len(signal.y):
        f_i = get_interpolated_function(origin_basis, signal.y, interp_methods)
        new_y = f_i(new_basis)
    else:
        new_y = signal.y
    attrs = dict(signal.signal().attr.items())
    new_raster.create_signal(signal.name, new_y, attrs)

def get_interpolated_function(tb_old, ts_old, interp_methods):
    """Get interplated function from timbase and timeserie."""
    def datetime_wrapper(interp):
        def dt_inner(tb_new):
            tb_old = (tb_new - tb_new[0]) / timeunit
            return interp(tb_old)
        return dt_inner

    bool_interp_method = interp_methods[0]
    int_interp_method = interp_methods[1]
    float_interp_method = interp_methods[2]

    if tb_old.dtype.kind == 'M':
        tb_is_datetime = True
    else:
        tb_is_datetime = False
    timeunit = np.timedelta64(1, 'us')

    kind = ts_old.dtype.kind
    if kind in ('b', 'S', 'U'):
        interp = bool_interp_method
    elif kind in ('i', 'u'):
        interp = int_interp_method
    else:
        interp = float_interp_method

    if interp == 'nearest':
        return nearest_any(tb_old, ts_old)
    elif interp == 'zero':
        return zero_any(tb_old, ts_old)

    if tb_old.size == ts_old.size == 1:
        # Signals with one sample can only be resampled using 'nearest' or
        # 'zero'.
        sywarn("Can't interpolate signal with one sample using method '{}', "
               "falling back to method 'nearest'".format(interp))
        return nearest_any(tb_old, ts_old)
    else:
        if tb_is_datetime:
            tb_old = (tb_old - tb_old[0]) / timeunit
        f_i = interp1d(tb_old, ts_old, kind=interp, bounds_error=False)

    if tb_is_datetime:
        return datetime_wrapper(f_i)
    else:
        return f_i

def zero_any(tb_old, ts_old):
    """Returns nearest previous neighbour function for tb_old and ts_old."""
    def zero_inner(tb_new):
        if len(tb_old) == 0:
            raise SyDataError('Empty (zero rows) rasters are not supported.')
        elif len(tb_old) == 1:
            result = np.array([ts_old[0]] * len(tb_new))
        else:
            # This mask tells us what data points to use. It is true for
            # the last value for any sequence of equal time stamps.
            mask = np.append((tb_old[1:] != tb_old[:-1]), True)

            f = interp1d(tb_old[mask], np.flatnonzero(mask),
                         bounds_error=False, fill_value=-1)
            if any(np.isnan(tb_new)):
                sywarn("NaNs in tb_new")
            i_new = f(tb_new)
            if any(np.isnan(i_new)):
                sywarn("NaNs in i_new")

            result = ts_old[list(i_new)]

        # Samples that aren't covered by the tb_old domain should be "empty".
        # This is as close to "empty" as we can get without implementing masked
        # arrays.
        too_early = tb_new < tb_old[0]
        if result.dtype.kind in ('f', 'c'):
            result[too_early] = np.nan
        elif result.dtype.kind in ('i', 'u', 'b', 'm', 'M'):
            result[too_early] = 0
        elif result.dtype.kind in ('S', 'U'):
            result[too_early] = ''
        else:
            raise TypeError('Unknown dtype: {}'.format(result.dtype))
        return result
    return zero_inner

def nearest_any(tb_old, ts_old):
    """Returns nearest neighbour function for tb_old and ts_old."""
    def nearest_inner(tb_new):
        if len(tb_old) == 1:
            result = np.array([ts_old[0]] * len(tb_new))
        else:
            f = interp1d(tb_old, np.arange(len(tb_old)), bounds_error=False)
            i_new = f(tb_new)
            i_new += 0.5

            # If the old time basis starts with multiple data points with the
            # same time stamp, the interpolation will give NaN values for that
            # time. Since this only happens at the start we can treat any NaN
            # values as being too early.
            too_early = np.logical_or(tb_new < tb_old[0], np.isnan(i_new))
            too_late = tb_new > tb_old[-1]
            i_new[too_early] = 0
            i_new[too_late] = -1

            result = ts_old[list(i_new)]
        return result
    return nearest_inner

def interpolate_with_spec(spec, adaf_obj):
    out_adaffile = adaf.File()
    out_adaffile.meta.from_table(adaf_obj.meta.to_table())
    out_adaffile.res.from_table(adaf_obj.res.to_table())
    signals, dts, to_tbs = spec

    dt_to_signals = collections.defaultdict(list)
    tbname_to_signals = collections.defaultdict(list)
    for i, (dt, to_tb, signal) in enumerate(zip(dts, to_tbs, signals)):
        if not np.isnan(dt):
            dt_to_signals[dt].append(signal)
        elif to_tb:
            tbname_to_signals[to_tb].append(signal)
        else:
            raise SyDataError("Row {} in specification table specifies "
                              "neither dt nor a target time basis.".format(i))

    new_timebases = []
    for dt, dt_signals in dt_to_signals.items():
        # Create output system/raster
        new_timebasis, unit = get_new_timebasis(adaf_obj, dt, dt_signals)
        system_name = 'Resampled system'
        raster_name = 'Resampled raster {:.2}'.format(dt)
        new_timebases.append(
            (system_name, raster_name, new_timebasis, unit, dt_signals))
    for tbname, tb_signals in tbname_to_signals.items():
        raster_dict = get_raster_dict(adaf_obj)
        try:
            old_system_name, old_raster_name = raster_dict[tbname]
        except KeyError:
            sywarn('No such system/raster: {}'.format(tbname))
            continue
        old_tb_column = (
            adaf_obj.sys[old_system_name][old_raster_name].basis_column())

        system_name = 'Resampled system'
        raster_name = old_raster_name
        new_timebasis = old_tb_column.value()
        unit = old_tb_column.attr['unit'] or 's'
        new_timebases.append(
            (system_name, raster_name, new_timebasis, unit, tb_signals))

    for i, (system_name, raster_name, new_timebasis, unit,
            signals) in enumerate(new_timebases):
        if not unit:
            unit = 's'
        if system_name not in out_adaffile.sys.keys():
            new_system = out_adaffile.sys.create(system_name)
        if raster_name not in new_system.keys():
            new_raster = new_system.create(raster_name)
        new_raster.create_basis(new_timebasis, attributes={'unit': unit})

        # Loop over all signals and resample them
        for i_signal, signal_name in enumerate(signals):
            if signal_name not in adaf_obj.ts.keys():
                continue
            signal = adaf_obj.ts[signal_name]
            origin_raster_name = signal.raster_name()
            origin_system_name = signal.system_name()
            origin_raster = (
                adaf_obj.sys[origin_system_name][origin_raster_name])
            resample_signal(origin_raster, new_raster, signal)

    return out_adaffile

def interpolate(adaf_obj):
    RemoveETKC(adaf_obj)
    RenameCrankAngleRaster(adaf_obj)

    # get spec
    spec = get_spec()
    # interpolate with spec
    new_adaf_obj = interpolate_with_spec(spec, adaf_obj)
    return new_adaf_obj
