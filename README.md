# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

In order to run the Neurobazaar Platform you need to have at least Python **3.11** installed on your computer.

This software uses VTK version 9.3.1.

This software has been developed and tested with Python **3.11** on Ubuntu 22.04 LTS.

### VTK Setup

Before you can build VTK, you need to initalize the VTK submodule.

```
git submodule init
git submodule update
```

### Python Virtual Environment Setup

All of the required Python packages are installed in a Python Virtual Environment. The first step is to create the virtual environment and the second step is to load/activate the environment. The first step has to be run only once.

Create the Python Virtual Environment on Ubuntu 22.04 LTS:  
```
python3.11 -m venv .venv  
```

Load/activate the Python Virtual Environment in Ubuntu 22.04 LTS: 
```
source .venv/bin/activate
```

### Install the Python Dependencies/Packages

Install the dependecies/packages on the loaded/activated virtual environment:
```
python -m pip install -r requirements.txt
```

## How to Build and Run

Migrate the Django database (only required to run once):
```
python manage.py migrate
```

Start the Django server:
```
python manage.py runserver   
```
