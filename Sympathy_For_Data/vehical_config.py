import datetime
import numpy as np
import pandas as pd

vehical_config_file = "vehicle_config.xlsx"


def vehical_config(adaf_objs):
    """
    update the adaf's meta data from vehical config
    """
    config = get_config()
    matched_list = look_up(adaf_objs, config)
    update_meta(adaf_objs, matched_list)


def get_config():
    # load the config file
    xls_config = pd.ExcelFile(vehical_config_file)
    config = xls_config.parse('Sheet1')

    # convert datatime to date
    convert_datetime_to_date(config)

    grouped = config.groupby("VIN")
    new_groups = []
    for name, group_ in grouped:
        group_ = group_.sort_values(by="date")
        fill_gap(group_)
        new_groups.append(group_)
    config = pd.concat(new_groups)
    config = config.sort_values(by='date')
    return config


def update_meta(adaf_objs, matched_list):
    for i, adaf_obj in enumerate(adaf_objs):
        adaf_obj.meta.delete_column("Date")
        adaf_obj.meta.delete_column("VIN_Number")
        if type(matched_list[i]) == type(None):
            continue

        matched_config = matched_list[i]
        for key in matched_config.keys():
            if key != "date":
                adaf_obj.meta.create_column("{}_{}".format("VehicleList", key),
                                            np.array([matched_config[key]]))

        # mdf_date iso format
        MDF_date = adaf_obj.meta["MDF_date"].value()
        MDF_date_iso_format = unicode(datetime.datetime.strptime(MDF_date[0], "%d:%m:%Y").strftime(u"%Y-%m-%d"))
        adaf_obj.meta.create_column("UserMeta_mdf_date_isoformat", np.array([MDF_date_iso_format]))

        # engine running
        if 'CoEng_st' in adaf_obj.ts.keys():
            engine_running = np.any(adaf_obj.ts['CoEng_st'].y == 3)
        else:
            engine_running = False

        description = u'True if the engine is ever running (CoEng_st == 3)'
        adaf_obj.meta.create_column('UserMeta_EngingRunning', np.array([engine_running]),
                                     {'description': description})


def look_up(adaf_objs, config):
    matched_list = []
    for adaf_obj in adaf_objs:
        adaf_vin = adaf_obj.meta["VIN_Number"].value()[0]
        found = False
        for index, row in config.iterrows():
            config_vin = row["VIN"]
            if is_vin_match(adaf_vin, config_vin):
                matched_list.append(row)
                found = True
                break
        if not found:
            matched_list.append(None)
    return matched_list


def is_vin_match(adaf_vin, config_vin):
    adaf_vin_list = list(adaf_vin)
    config_vin_list = list(str(config_vin))
    for i, num in enumerate(adaf_vin_list):
        if num == '?':
            continue
        else:
            if num != config_vin_list[i]:
                return False
    return True


def fill_gap(group_):
    """
    use the last item's value to fill the empty
    """
    columns = ["engine", "transmission", "Reg No"]
    for column in columns:
        series = group_[column]
        series.fillna(method="ffill", inplace=True)


def convert_datetime_to_date(config):
    """
    already date, no need to convert
    """
    pass


if __name__ == "__main__":
    vehical_config(None)
