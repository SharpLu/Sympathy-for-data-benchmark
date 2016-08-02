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
#input_dir = "./data"
input_dir = "/home/ubuntu/Downloads/data"
# output dir
output_dir = "./output"


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
        adaf_obj.meta.create_column('Date', np.array([os.path.dirname(os.path.abspath(input_dir))]))
    adaf_objs.sort(key=lambda x: x.meta['Date'].value()[0])


def main():
    sydata_adaf_objs = []
    dat_list, sydat_list = get_data()
    # sydat
    new_sydat_list = []
    for sydat in sydat_list:
        try:
            adaf_obj = adaf.File(filename=sydat)
            sydata_adaf_objs.append(adaf_obj)
            new_sydat_list.append(sydat)
        except:
            print("Can't input sydata file {}".format(sydat))

    # dat
    dat_adaf_objs = []
    processed_adaf_objs = []
    importer = mdf_importer.MdfImporter("latin1", None)

    new_dat_list = []
    for dat in dat_list:
        try:
            adaf_obj = adaf.File()
            importer.run(dat, adaf_obj)
            dat_adaf_objs.append(adaf_obj)
            new_dat_list.append(dat)
        except:
            print("Can't import dat file {}".format(dat))
    for adaf_obj in dat_adaf_objs:
        ExtractVIN(adaf_obj)
        processed_adaf_objs.append(process_dat_adaf(adaf_obj))
    #
    # update meta
    for i, adaf_obj in enumerate(sydata_adaf_objs):
        update_file_path_meta(adaf_obj, new_sydat_list[i], input_dir, output_dir)

    for i, adaf_obj in enumerate(processed_adaf_objs):
        update_file_path_meta(adaf_obj, new_dat_list[i], input_dir, output_dir)

    adaf_objs = sydata_adaf_objs + processed_adaf_objs

    # sort
    sort_adafs(adaf_objs)

    # vehical_config
    vehical_config(adaf_objs)
    #
    # filter file
    adaf_objs = filter_file(adaf_objs)

    # create subsets
    subsets_list = create_subsets(adaf_objs)

    # loop the subsets to do evaluation
    for subsets in subsets_list:
        eval_flow(subsets, output_dir)

    # dump
    for adaf_obj in adaf_objs:
        out_name = adaf_obj.meta["DATA_Name"].value()[0]
        out_name = out_name.split(".")[0] + ".sydata"
        file_path = os.path.join(output_dir, out_name)
        with adaf.File(filename=file_path, mode='w', source=adaf_obj):
            pass

if __name__ == "__main__":
    import time
    start_time = time.time()
    main()
    print("--- %s seconds ---" % (time.time() - start_time))
