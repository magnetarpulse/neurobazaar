# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  
- Nimisha Vidyadhar Bhoir 2024 (nbhoir@depaul.edu)  
- Rushikesh Rajendra Suryawanshi 2024 (rsuryawa@depaul.edu) 

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

### Install Python

In order to run the Neurobazaar Platform you need to have at least Python **3.11** installed on your computer.

For Windows 10 this software has been tested with Python **3.11.5**.

### Set up the Python Virtual Environment

All of the required Python packages are installed in a Python Virtual Environment.

To create the Python Virtual Environment in Windows 10 use the following command (you only need to create it once):
```
py -3.11 -m venv .venv
```
To create the Python Virtual Environment in MacOS use the following command (you only need to create it once):  
```
: python3.11 -m venv .venv  
```



To load/activate the Python Virtual Environment in Windows 10 Powershell use the following command:
```
.venv/Scripts/Activate.ps1
```

To load/activate the Python Virtual Environment in Windows 10 CMD use the following command:
```
.venv/Scripts/activate.bat
```
To load/activate the Python Virtual Environment in Mac OS use the following command: 
```
source .venv/bin/activate
```
  


### Install the Python Required Packages
For Mac os as well as Windows OS
To install the required Python packages inside the loaded/activated virtual enviroment run the following command:
```
python -m pip install -r requirements.txt
```


### How to install Django on cmd or Terminal
for Windows: 
```
pip install django  
```
for MacOS
```
pip3 install django  
```

###Check django version: 
```
python -m django –version (Windows)
```

```
python -m django –version  (MacOS)
```

## How to Build and Run Django application
```
python manage.py runserver   ---> for Windows
```
```
python3 manage.py runserver   ---> for MacOS
```