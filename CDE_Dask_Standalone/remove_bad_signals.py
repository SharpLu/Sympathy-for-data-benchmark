
bad_signal_file = "bad_cols.csv"

def get_bad_signals(bad_file):
    bad_signals = []
    with open(bad_file) as f:
        con = f.readlines()
        for line in con[1:]: # ignore the title line
            line = line.strip()
            if line:
                tmp = line.split(";")
                if len(tmp) > 2:
                    sig_str = tmp[0]
                    sig_str = sig_str.strip("\"")
                    sig_str = sig_str.strip("'")
                    bad_signals.append(sig_str)
    return bad_signals


def remove_bad_signals(adaf_obj):
    bad_signals = get_bad_signals(bad_signal_file)
    for system_name in adaf_obj.sys.keys():
        system = adaf_obj.sys[system_name]
        need_remove = []
        for raster_name in system.keys():
            raster = system[raster_name]
            for sig_name in raster.keys():
                if sig_name in bad_signals:
                    need_remove.append(raster_name)
                    break
        for raster_name in need_remove:
            print("Remove raster: {}".format(raster_name))
            del system[raster_name]
