# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean (aorhean@depaul.edu)  

Scalable Interactive Visualization Platform for Machine Learning and Data Science.

## Requirements and Setup

### Development Environment and Python

This software has been tested on:
- Windows 10/11 (Python **3.11**)
- Ubuntu 22.04 LTS (Python **3.11**).

### Python Virtual Environment

This project uses the Python virtual enviroment to configure software depdendecies.

#### Windows 10/11

Create the Python Virtual Environment:
```
py -3.11 -m venv .venv
```

Load/activate the Python Virtual Environment in Powershell:
```
.venv/Scripts/Activate.ps1
```

Load/activate the Python Virtual Environment in CMD:
```
.venv/Scripts/activate.bat
```

#### Ubuntu 22.04 LTS (includes WSL2)

Create the Python Virtual Environment:
```
python3.11 -m venv .venv
```

Load/activate the Python Virtual Environment:
```
source .venv/bin/activate
```

### Install the Python Required Packages

Install the required Python packages inside the loaded/activated virtual enviroment:
```
python -m pip install -r requirements.txt
```

## How to Build and Run

Migrate the database:
```
python manage.py migrate
```

Start server:
```
python manage.py runserver
```
