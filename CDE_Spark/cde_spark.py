import datetime
import os
import time

import numpy as np

import mdf_importer
from cde_functions_new import ExtractVIN, RemoveETKC, RenameCrankAngleRaster
from cde_plot import distribution_plot_subsets_spark
from eval_flow import eval_flow_spark
from filter_file import do_filter
from interpolate import interpolate, interpolate_with_spec, get_spec
from pyspark import SparkContext, SparkConf, StorageLevel
from remove_bad_signals import get_bad_signals
from sympathy.api import adaf
from update_meta import update_file_path_meta
from vehical_config import look_up_and_update_metadata_spark, get_config_spark

os.environ["SPARK_HOME"] = "/home/ubuntu/spark-1.6.1-bin-hadoop2.6"

# ban sinal file config
bad_signal_file = "bad_cols.csv"
# vehical config
vehical_config_file = "vehicle_config.xlsx"
# data input dir suffix by *.dat
input_dir = "/home/cocky/workspace/spark-1.6.1-bin-hadoop2.6/cde_data/*.dat"
#output dir
output_dir = "/home/cocky/workspace/spark-1.6.1-bin-hadoop2.6/cde_output"
# standalone URL: spark://cocky:7077
# localhost URL: local[*]
master = "local[*]"
# app Name
app_name = "cde-test"

conf = SparkConf().setAppName(app_name)
#.setMaster(master)

sc = SparkContext(conf=conf)

bc_bad_signals = sc.broadcast(get_bad_signals(bad_signal_file))
bc_vehical_config = sc.broadcast(get_config_spark(vehical_config_file))
bc_output_dir = sc.broadcast(output_dir)
bc_spec = sc.broadcast(get_spec())


def read_dat_hdfs(x):
    """
    read file by name and serialize
    :param dat_file_name:
    :return:
    """
    dat_file_name = x[0]
    data_buffer = x[1]
    importer = mdf_importer.MdfImporter("latin1", None)
    adaf_obj = adaf.File()
    importer.run_spark(dat_file_name, adaf_obj, data_buffer)
    update_file_path_meta(adaf_obj, dat_file_name, input_dir, bc_output_dir.value)

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

def interpolate(adaf_obj):
    RemoveETKC(adaf_obj)
    RenameCrankAngleRaster(adaf_obj)

    # interpolate with spec
    new_adaf_obj = interpolate_with_spec(bc_spec.value, adaf_obj)
    return new_adaf_obj

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
    file_path = os.path.join(bc_output_dir.value, out_name)

    with adaf.File(filename=file_path, mode='w', source=adaf_obj):
        pass


def saveSydata_hdfs(adaf_obj):
    """
    dump the final file
    :param adaf_obj:
    :return:
    """
    out_name = adaf_obj.meta["DATA_Name"].value()[0]
    out_name = out_name.split(".")[0] + ".sydata"
    file_path = os.path.join(bc_output_dir.value, out_name)
    with adaf.File(filename=file_path, mode='w', source=adaf_obj):
        pass


# TODO no sort just for some metadata
def sort_adaf(adaf_obj):
    MDF_date = adaf_obj.meta["MDF_date"].value()
    MDF_time = adaf_obj.meta["MDF_time"].value()
    date = np.array([datetime.datetime.strptime(d + t, "%d:%m:%Y%H:%M:%S") for d, t in zip(MDF_date, MDF_time)])
    adaf_obj.meta.create_column('Date', np.array([os.path.dirname(os.path.abspath(input_dir))]))
    return adaf_obj

def vehical_config(adaf_obj):
    return look_up_and_update_metadata_spark(adaf_obj, bc_vehical_config.value)


def subsetMetaData(adaf_obj):
    field0 = adaf_obj.meta["FILENAME_field_0"].value()[0]
    adaf_obj.meta.create_column("DATASET_subgroup", np.array(["FILENAME_field_0: {}".format(field0)]))
    adaf_obj.meta.create_column('DATASET_Workflow_name', np.array(["B_KatDiagnos"]))

    return adaf_obj


# (field0, series.y)
def eval_flow_cde(x):
    return eval_flow_spark(x, bc_output_dir.value)

def plotImage(x):
    t0 = time.time()
    distribution_plot_subsets_spark(x[1], bc_output_dir.value)
    print "plotImage used:  ", t0 - time.time()
    # print("-----"+x[0],x[1])

# hdfs
startTime = time.time()
t0 = time.time()
hdfsFile = sc.binaryFiles(input_dir).persist(StorageLevel.MEMORY_AND_DISK)
#########################################################Total Time Used: 8.73000001907
adaf_objs = hdfsFile.map(read_dat_hdfs)\
    .map(ExtractVIN) \
    .map(process_dat_adaf).map(sort_adaf) \
    .map(vehical_config) \
    .filter(do_filter)\
    .map(subsetMetaData)
#########################################################Total Time Used: 25.1680002213

# rdd_vehical_config = hdfsFile.map(read_dat_hdfs) \
#     .map(ExtractVIN) \
#     .map(process_dat_adaf).map(sort_adaf) \
#     .map(vehical_config)
# rdd_vehical_config.count()
# print("rdd_vehical_config Used Time: {}".format(time.time() - t0))
# t0 = time.time()
# rdd_filter = rdd_vehical_config.filter(do_filter)
# rdd_filter.count()
# print("rdd_filter Used Time: {}".format(time.time() - t0))
# t0 = time.time()
#
# adaf_objs = rdd_filter.map(subsetMetaData)
# adaf_objs.count()
# print("subset Used Time: {}".format(time.time() - t0))
# t0 = time.time()
#############################################################

# adaf_objs.map(eval_flow_cde).groupByKey().foreach(plotImage)

# save
adaf_objs.foreach(saveSydata)

print("save sydata Time: {}".format(time.time() - t0))
#sc.stop()
# plot to dataframe and groupby field0

print("Total Time Used: {}".format(time.time()- startTime))

