"E:\data\BaiduYunDownload\PySpark_CDE\PySpark_CDE\04-18\CDE_04_17\data\*.dat"
import os
import numpy as np
import datetime

from cde import get_data
from cde_functions_new import ExtractVIN
import mdf_importer
from pyspark import SparkContext, SparkConf
from interpolate import interpolate
from remove_bad_signals import get_bad_signals
from sympathy.api import adaf
from update_meta import update_file_path_meta
from vehical_config import get_config, vehical_config_spark, look_up_and_update_metadata_spark

bad_signal_file = "bad_cols.csv"
# input dir
input_dir = "/home/ubuntu/Downloads/Example_data/"
# output dir
output_dir = "./output"

os.environ["SPARK_HOME"] = "/home/ubuntu/spark-1.6.1-bin-hadoop2.6"

conf = SparkConf().setAppName("cde-test").setMaster("local[1]")

sc = SparkContext(conf=conf)

bc_bad_signals = sc.broadcast(get_bad_signals(bad_signal_file))
bc_vehical_config = sc.broadcast(get_config())
#allFile = sc.wholeTextFiles("E:\\tmp\\data")
dat_list, sydat_list= get_data()
allFile = sc.parallelize(dat_list)

def read_dat(dat_file_name):
    """
    read file by name and serialize
    :param dat_file_name:
    :return:
    """
    importer = mdf_importer.MdfImporter("latin1", None)
    adaf_obj = adaf.File()
    importer.run(dat_file_name, adaf_obj)
    update_file_path_meta(adaf_obj, dat_file_name, input_dir, output_dir)
    return adaf_obj

def remove_bad_signals(adaf_obj):
    """
    remove the bad signals
    :param adaf_obj:
    :return:
    """
    for system_name in adaf_obj.sys.keys():
        system = adaf_obj.sys[system_name]
        need_remove = []
        for raster_name in system.keys():
            raster = system[raster_name]
            for sig_name in raster.keys():
                if sig_name in bc_bad_signals.value:
                    need_remove.append(raster_name)
                    break
        for raster_name in need_remove:
            print("Remove raster: {}".format(raster_name))
            del system[raster_name]

def process_dat_adaf(adaf_obj):
    remove_bad_signals(adaf_obj)
    new_adaf_obj = interpolate(adaf_obj)
    return new_adaf_obj

def saveSydata(adaf_obj):
    """
    dump the final file
    :param adaf_obj:
    :return:
    """
    out_name = adaf_obj.meta["DATA_Name"].value()[0]
    out_name = out_name.split(".")[0] + ".sydata"
    file_path = os.path.join(output_dir, out_name)
    with adaf.File(filename=file_path, mode='w', source=adaf_obj):
        pass


#TODO no sort just for some metadata
def sort_adaf(adaf_obj):
        MDF_date = adaf_obj.meta["MDF_date"].value()
        MDF_time = adaf_obj.meta["MDF_time"].value()
        date = np.array([datetime.datetime.strptime(d + t, "%d:%m:%Y%H:%M:%S") for d, t in zip(MDF_date, MDF_time)])
        adaf_obj.meta.create_column('Date', np.array([os.path.dirname(os.path.abspath(input_dir))]))
        return adaf_obj


def vehical_config(adaf_obj):
    return look_up_and_update_metadata_spark(adaf_obj, bc_vehical_config.value)

allFile.map(read_dat)\
    .map(ExtractVIN)\
    .map(process_dat_adaf).map(sort_adaf)\
    .map(vehical_config)\
    .foreach(saveSydata)
