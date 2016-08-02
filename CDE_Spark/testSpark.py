import numpy as np

from pyspark import SparkConf, SparkContext

master = "local[*]"
# app Name
app_name = "cde-test"

conf = SparkConf().setAppName(app_name).setMaster(master)
sc = SparkContext(conf=conf)
nu = sc.parallelize([(11, np.array( [0, 1, 2])), (11, np.array([0, 1, 2])), (22, np.array([0, 1, 2]))])
def fff(x):
    for x in x[1]:
        print(x.ndim)
nu.groupByKey().foreach(fff)
