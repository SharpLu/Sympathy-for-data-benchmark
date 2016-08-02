import os
import datetime
import numpy as np
from sympathy.api import adaf
import mdf_importer
from dat_adaf_processer import process_dat_adaf
from update_meta import update_file_path_meta
from cde_functions_new import ExtractVIN
from vehical_config import vehical_config
from filter_file import filter_file
from create_subsets import create_subsets
from eval_flow import eval_flow

# input dir
input_dir = "/home/ubuntu/Downloads/data"
input_dir = "/home/ubuntu/Desktop/IT"
# output dir
output_dir = "./output"
# set size 9G
SET_SIZE = 10 * 1e9


def get_data():
    file_list = []
    for root, dirs, files in os.walk(input_dir):
        for file_ in files:
            file_path = os.path.join(root, file_)
            file_list.append(file_path)
    dat_list = [path for path in file_list if path.endswith(".dat")]
    sydat_list = [path for path in file_list if path.endswith(".sydata")]
    return dat_list, sydat_list


def sort_adafs(adaf_objs):
    for adaf_obj in adaf_objs:
        MDF_date = adaf_obj.meta["MDF_date"].value()
        MDF_time = adaf_obj.meta["MDF_time"].value()
        date = np.array([datetime.datetime.strptime(d + t, "%d:%m:%Y%H:%M:%S") for d, t in zip(MDF_date, MDF_time)])
        adaf_obj.meta.create_column('Date', date)
    adaf_objs.sort(key=lambda x: x.meta['Date'].value()[0])


def process_one_set(adaf_set, adaf_list):
    for dat, adaf_obj in adaf_set:
        ExtractVIN(adaf_obj)
        try:
            adaf_obj = process_dat_adaf(adaf_obj)
            update_file_path_meta(adaf_obj, dat, input_dir, output_dir)
            adaf_list.append(adaf_obj)
        except:
            print("Interpolate error {}".format(dat))


def main():
    adaf_objs = []
    dat_list, sydat_list = get_data()
    # sydat
    Dat_start_time = time.time()
    for sydat in sydat_list:
        try:
            adaf_obj = adaf.File(filename=sydat)
        except:
            print("Can't input sydata file {}".format(sydat))
            continue
        update_file_path_meta(adaf_obj, sydat, input_dir, output_dir)
        adaf_objs.append(adaf_obj)

    # dat
    importer = mdf_importer.MdfImporter("latin1", None)

    adaf_set = []
    cout_size = 0
    while len(dat_list) != 0:
        dat = dat_list[0]
        cur_size = os.stat(dat).st_size
        cout_size += cur_size
        if cout_size > SET_SIZE:
            process_one_set(adaf_set, adaf_objs)
            cout_size = 0
            adaf_set = []
        else:
            try:
                adaf_obj = adaf.File()
                importer.run(dat, adaf_obj)
            except:
                print("Can't import dat file {}".format(dat))
                dat_list.pop()
                continue
            adaf_set.append((dat, adaf_obj))
            dat_list.pop()

    if len(adaf_set) > 0:
        process_one_set(adaf_set, adaf_objs)

    # for dat in dat_list:
    #     try:
    #         adaf_obj = adaf.File()
    #         importer.run(dat, adaf_obj)
    #     except:
    #         print("Can't import dat file {}".format(dat))
    #         continue
    #     ExtractVIN(adaf_obj)
    #     adaf_obj = process_dat_adaf(adaf_obj)
    #     update_file_path_meta(adaf_obj, dat, input_dir, output_dir)
    #     adaf_objs.append(adaf_obj)

    # sort
    sort_adafs(adaf_objs)

    # dump

    # dump
    for adaf_obj in adaf_objs:
        out_name = adaf_obj.meta["DATA_Name"].value()[0]
        out_name = out_name.split(".")[0] + ".sydata"
        file_path = os.path.join(output_dir, out_name)
        with adaf.File(filename=file_path, mode='w', source=adaf_obj):
            pass

    dat_finished_time = time.time() - Dat_start_time
    print "%-40s%s" % ("dat to sydata processing take Seconds", dat_finished_time)

    # vehical_config
    vehical_config(adaf_objs)
    #
    # filter file
    adaf_objs = filter_file(adaf_objs)

    # create subsets
    subsets_list = create_subsets(adaf_objs)

    # loop the subsets to do evaluation
    eval_flow_start_time = time.time()
    for subsets in subsets_list:
        eval_flow(subsets, output_dir)
        eval_flow_finished_time = time.time() - eval_flow_start_time
    print "%-40s%s" % ("eval_flow_finished_time", eval_flow_finished_time)


if __name__ == "__main__":
    import time
    start_time = time.time()
    main()
    print("--- %s seconds ---" % (time.time() - start_time))
