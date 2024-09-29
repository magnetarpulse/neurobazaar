# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)
- Areena Mahek 2024 (amahek@depaul.edu)

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

To load/activate the Python Virtual Environment in Windows 10 Powershell use the following command:
```
.venv/Scripts/Activate.ps1
```

To load/activate the Python Virtual Environment in Windows 10 CMD use the following command:
```
.venv/Scripts/activate.bat
```

### Python Virtual Environment Setup

All of the required Python packages are installed in a Python Virtual Environment. The first step is to create the virtual environment and the second step is to load/activate the environment. The first command has to be run only once.

To create the Python Virtual Environment on Ubuntu 22.04 LTS or a newer Ubuntu version, run the following commands. 

**Note:** In this example, we are naming our Python Virtual Environment "**.venv**", but you can name it something else if you already have a Python Virtual Environment called .venv:  

```
python3.11 -m venv .venv
```

To load/activate the Python Virtual Environment on Ubuntu 22.04 LTS or a newer Ubuntu version: 

```
source .venv/bin/activate
```

### Install the Python Dependencies/Packages

Install the dependencies/packages on the loaded/activated virtual environment:

```
python -m pip install -r requirements.txt
```

### Execution

```
python ood_interface_matplotlib
```


