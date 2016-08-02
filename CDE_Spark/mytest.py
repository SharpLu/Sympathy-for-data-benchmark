import h5py
import dask.array as da
import sys
import os
from glob import glob
from pyspark import SparkContext
import pandas as pd
import re
import numpy as np
import pandas as pd

sc = SparkContext()

def print_hdf5_file_structure(file_name):
    file = h5py.File(file_name, 'r')  # open read-only
    print_hdf5_item_structure(file)
    file.close()

def print_hdf5_item_structure(g, offset=''):
    npdata = 0
    """Prints the input file/group/dataset (g) name and begin iterations on its content"""
    if isinstance(g, h5py.File):
        print g.file, '(File)', g.name

    elif isinstance(g, h5py.Dataset):
        # print '(Dataset)', g.name, '    len =', g.shape  # , g.dtype
        rdd = sc.parallelize(g.value)
        print '(Spark #)', g.name, '    len =', rdd.count()  # , g.dtype
        rdd.map(lambda x: not x.is_empty())
        rdd2 = rdd.filter(g.name =="/sys/INCA/data/Group24/data/NSCRgn_stIntrVirtAPPDNOx_mp\ETKC:1")

    elif isinstance(g, h5py.Group):
        print '(Group)', g.name

    else:
        print 'WORNING: UNKNOWN ITEM IN HDF5 FILE', g.name
        sys.exit("EXECUTION IS TERMINATED")

    if isinstance(g, h5py.File) or isinstance(g, h5py.Group):
        for key, val in dict(g).iteritems():
            subg = val
            # print offset, key, val  # ,"   ", subg.name #, val, subg.len(), type(subg),
            print_hdf5_item_structure(subg, offset + '    ')

if __name__ == "__main__":
    print_hdf5_file_structure('VED5_CMC559_CO_2014-09-11_02.sydata')
    sys.exit("End of test")
