# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

### System Requirements

In order to run the Neurobazaar Platform you need to have at least Python **3.11** installed on your computer.

This software has been developed and tested with Python **3.11** on:
- Windows 10
- Ubuntu 22.04 LTS

### Python Virtual Environment Setup

All of the required Python packages are installed in a Python Virtual Environment. The first step is to create the virtual environment and the second step is to load/activate the environment. The first step has to be run only once.

Create the Python Virtual Environment on Windows 10:
```
py -3.11 -m venv .venv
```

Create the Python Virtual Environment on Ubuntu 22.04 LTS or Mac OS 14:  
```
python3.11 -m venv .venv  
```

Load/activate the Python Virtual Environment in Windows 10 Powershell:
```
.venv/Scripts/Activate.ps1
```

Load/activate the Python Virtual Environment in Windows 10 CMD:
```
.venv/Scripts/activate.bat
```

Load/activate the Python Virtual Environment in Ubuntu 22.04 LTS or Mac OS 14: 
```
source .venv/bin/activate
```

### Install the Python Dependencies/Packages

Install the dependecies/packages on the loaded/activated virtual environment:
```
python -m pip install -r requirements.txt
```

## How to Build and Run

Start the Trame server(In different terminal):
```
cd trame
```
```
python server.py --server 
```

Start the Vue & Vite server(In different terminal):
```
npm install
```
```
npm run build
```
```
npm run dev
```

Start the Django client(In different terminal):
```
python manage.py makemigrations home
```
```
python manage.py migrate
```
```
python manage.py runserver   
```
