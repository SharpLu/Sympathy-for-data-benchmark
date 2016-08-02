import os
import numpy as np
import datetime


def update_file_path_meta(adaf_obj, file_path, input_dir, output_dir):
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    adaf_obj.meta.create_column('DATASET_Output_Path', np.array([output_dir]))
    adaf_obj.meta.create_column('DATASET_Path', np.array([input_dir]))
    adaf_obj.meta.create_column('DATA_Name', np.array([os.path.basename(file_path)]))
    adaf_obj.meta.create_column('DATASET_Name', np.array([os.path.basename(os.path.abspath(file_path).rsplit(".")[1])]))
    tmp = os.path.basename(file_path).split("_")
    for i, field in enumerate(tmp):
        adaf_obj.meta.create_column('FILENAME_field_{}'.format(i), np.array([field]))
    #MDF_date = adaf_obj.meta["MDF_date"].value()
    #MDF_time = adaf_obj.meta["MDF_time"].value()
    #date = np.array([datetime.datetime.strptime(d + t, "%d:%m:%Y%H:%M:%S") for d, t in zip(MDF_date, MDF_time)])
    #adaf_obj.meta.create_column('Date', np.array([os.path.dirname(os.path.abspath(input_dir))]))

