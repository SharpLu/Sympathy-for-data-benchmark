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
input_dir = "C://Users//FLU2//Documents//Input_data"
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
        adaf_obj.meta.create_column('Date', date)
    adaf_objs.sort(key=lambda x: x.meta['Date'].value()[0])


def main():
    adaf_objs = []
    dat_list, sydat_list = get_data()
    # sydat
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

    for dat in dat_list:
        try:
            adaf_obj = adaf.File()
            importer.run(dat, adaf_obj)
        except:
            print("Can't import dat file {}".format(dat))
            continue
        ExtractVIN(adaf_obj)
        adaf_obj = process_dat_adaf(adaf_obj)
        update_file_path_meta(adaf_obj, dat, input_dir, output_dir)
        adaf_objs.append(adaf_obj)

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
