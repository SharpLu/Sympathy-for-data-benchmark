



Sympathy for data benchmark


2016-05-25



Contents

1. Sympathy for data platform Spark as engine 
2. Sympathy for data benchmark execution environment 
3. Sympathy for data CDE workflow (pure python code) 
4. Sympathy for data Dask
5. Sympathy for data Spark

	

1 .  Sympathy for data platform Spark as engine 
If you experience any problem, please contact me, reply within 24hours.

1 . First make sure VMware workstation 12 pro or Virtualbox  has installed , then use your VM open the virtual machine.(Virtual machine.zip)
2 . Uncompress the Python Library.zip files to your Sympathy for data library folder(Example below)
C:\Program Files (x86)\SysESS\SympathyForData\1.3\Python27\Lib\site-packages 
3. Please copy the Lib files node_spark.py cde_spark.tmpl and bottle.py to your CDE library folder. The template file cde_spark.tmpl , you can configuration your execution partition number and spark installation directory
Example below
C:\Users\FLU2\Documents\CDE\cde_lib\Library\CDE
4. Re-load sympathy for data library 
5. Import the CDE workflow (cde.syx), and right click the spark importer node, you can configuration the information accordingly.(CDE folder)
Host: Your Virtual machine IP
Port : 22
User: sparkmaster
Password: 123456
The local directory:  as your data source folder(shared folder with your virtual machine)
After spark processing the Sydata files, will store at the local directory folder.
Remove Directory: find the windows shared folder path at Virtual machine.
Spark Directory: the spark install path at your Virtual machine.
Run.sh : Used to submit the execution tasks.

Figure 1 Spark import node
6. If the above steps configure correct, right execution the spark importer node will generate sydata to your shared folder.
C:\Users\FLU2\Documents\CDE\cde_lib\Library\CDE

2 . Sympathy for data benchmark execution environment\

Before you open the below benchmarks, suggestion you use Pycharm and Python Anaconda environment 
Please make sure you have installed the packages.
conda install pyside
conda install pyodbc
conda install scipy=0.15.0  numpy=1.9.1
conda install pywin32

When you first time execute the benchmark maybe will have unpredictable issues, most issues from the scipy version number, sympathy only support scipy=0.14.0 and 0.15.0, If you have higher scipy version may conflict with your anaconda packages such as numpy.

If you can still not solve the issues please check your sympathy library version the folder at :
C:\Program Files (x86)\SysESS\SympathyForData\1.3\Python27\Lib\site-packages
 



3. Sympathy for data CDE workflow (pure python code) 
	Code at Benchmark folder
1. Use Pycharm load the project, execution cde_timer.py
2. Annaconda as your project interpreter 
3. configuration the input and output folder at cde_start.py
4. execution cde_start.py
4. Sympathy for data Dask
Code at Benchmark folder
1. Use Pycharm load the project, execution cde_timer.py
2. Annaconda as your project interpreter 
	3. Make sure you have installed conda install dask
4. configuration the input and output folder at cde_start.py
5. Sympathy for data Spark
	Code at Benchmark folder
	•	Please download spark and configuration accordingly 
http://www.trongkhoanguyen.com/2014/11/how-to-install-apache-spark-121-in.html
2. Configuration the Poject interpreter as spark.
https://www.youtube.com/watch?v=u-P4keLaBzc 
3.  Spark as your python interpreter 
4.  If you experience can not find python packages , please import the package to your spark interpreter
C:\Anaconda2\Lib\site-packages


