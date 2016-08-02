工程安装
-------
1. conda install pyside
2. conda install pyodbc
sympathy depends on these two packages

3. copy sylib from   \SysESS\SympathyForData\1.3\Library\Common
4. copy sympath from \SysESS\SympathyForData\1.3\Sympathy\Python


cde spark
------
1. 入口地址 cde_spark.py
2. 测试之前需要配置环境变量为 SPARK_HOME
2. 本地测试修改 master为local[3]
3. 分布式测试,需要考虑依赖和讲master修改为spark://{ip}:{port}
4. 测试包运行命令{CDE_HOME}:python cde_spark.py

cde 分布式运行
---------
standalone cmd ：
`bin\spark-submit --master  spark://cocky:7077  --supervise  --executor-memory 6G --total-executor-cores 2 --py-files cde.zip cde_spark.py`
1. 其中cde直接将工程压缩就可以了。
2. --master为工程 为运行模式
3. 其他参数根据集群情况而定


单机跑
----------
修改配置：
```
#ban sinal file config
bad_signal_file = "bad_cols.csv"
#vehical config
vehical_config_file = "vehicle_config.xlsx"
#data input dir suffix by *.dat
input_dir = "E:\\data\\BaiduYunDownload\\PySpark_CDE\\PySpark_CDE\\04-18\\Example_data\\Example_data\\*.dat"
#output dir
output_dir = "./output"
#standalone URL: spark://cocky:7077
#localhost URL: local[*]
master = "local[*]"
#app Name
app_name = "cde-test"
```