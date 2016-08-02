"""
filter the input file
then add the filter meta to adaf
"""
import os
import numpy as np


def filter_file(adaf_objs):
    filterd_adafs = []
    for adaf_obj in adaf_objs:
        if do_filter(adaf_obj):
            filterd_adafs.append(adaf_obj)

    ## update meta
    for adaf_obj in filterd_adafs:
        adaf_obj.meta.create_column("DATASET_filter_filecount", np.array([len(filterd_adafs)]))
        adaf_obj.meta.create_column("DATASET_total_filecount", np.array([len(adaf_objs)]))

    ## output filter log to output dir
    log(filterd_adafs)
    return filterd_adafs

def filter_file_spark(adaf_obj):
    do_filter(adaf_obj)

    adaf_obj.meta.create_column("DATASET_filter_filecount", np.array([len(filterd_adafs)]))
    adaf_obj.meta.create_column("DATASET_total_filecount", np.array([len(adaf_objs)]))

    ## output filter log to output dir

    return adaf_obj

def log(filterd_adafs):
    log_msg = \
"""Selected Meta Filter:
AllData
*********************************
Running CDE for files:
{}"""
    if not filterd_adafs:
        return
    data_name_list = [adaf_obj.meta["DATA_Name"].value()[0] for adaf_obj in filterd_adafs]
    log_content = log_msg.format("\n".join(data_name_list))
    output_dir = filterd_adafs[0].meta["DATASET_Output_Path"].value()[0]
    log_path = os.path.join(os.path.abspath(output_dir), "FilterInfo.txt")
    with open(log_path, 'w') as f:
        f.write(log_content)


def do_filter(adaf_obj):
    """
    use all data now
    """

    adaf_obj.meta.create_column("DATASET_filter", np.array(["AllData"]))

    ##filter error column data
    try:
        signal_name = "OxiCat_facHCCnvRat"
        adaf_obj.ts[signal_name]
    except Exception ,e:
        print "no this column signal_named : {}".format(signal_name)
        return False

    return True
