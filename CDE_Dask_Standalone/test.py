import dask.array as da
print da.ones(5,chunks=2).visualize(filename='hello.svg')