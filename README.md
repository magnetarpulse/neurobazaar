# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

### Using the Neurobaazar

To use the services provieded by the Neurobaazar, there is no requirement, besides a web broswer and internet connection to access and use the services provided by the Neurobaazar. 

### Install Python

All tests have been conducted on **Python version 3.10**.

To build the stable interactive visualization service(s) of the Neurobazaar, you will need to install at least **Python version 3.10**.

### How to install Python (Apple macOS)
There are two ways to install Python on macOS machines.

&nbsp;&nbsp;&nbsp;&nbsp;**A:** Install **Python version 3.10** or higher from the offical Python website: **https://www.python.org/downloads/**.

&nbsp;&nbsp;&nbsp;&nbsp;**B:** From the command line interface:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**1:** Open the terminal. The terminal can be opened from the "spotlight search" (the magnifying glass) on the top right of the display and type "Terminal" and press enter. Alternatively, go to the "Finder", then go to the "Applications", and look for "Utilities" in "Applications". Open the "Utilities folder" and find the "Terminal" application. Double click on the "Terminal" application and it should open.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**2:** You should have the terminal open now. Before installing Python, I would make sure that you do not have Python3.10 or higher installed already. To do this, copy and paste the command **python3 --version** into the terminal. This command will return the Python3.xx version if the machine can find a Python version. If you already have Python3.10 or higher, then you do not need to go through the process of installing Python again. If you do not have Python (returned nothing) or have a Python version that is older than Python3.10, then I would reccomend to install Python following the steps below.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**3:** You should have the terminal open now. In the terminal, copy and paste **"/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"** then press enter. You can skip this step if you already have Homebrew installed. You can check if you have Homebrew installed from your terminal by copying and pasting this command: **brew --version** and then press enter. If Homebrew is installed, the command will return the version of Homebrew. I would make sure to check if you have Homebrew installed before you copy and paste the command and after you have installed Homebrew.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**4(optional):** As good practice, you should probably copy and paste the command **brew update** after installing Homebrew to ensure that nothing is incorrect or went wrong when installing Homebrew. 

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**5:** Once you have Homebrew installed, copy and paste the command **brew install python@3.10**. This will install the Python version 3.10. However, if you want to install a newer version of Python, you can do **brew install python@3.xx**, where xx is the Python version you want to install (assuming that the latest version is still Python 3.xx). 

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**6(optional):** After installing Python3.10 or higher, I would recommend to run the command **python3 --version** as this will save a lot of future problem. This command will return the python3.xx version if Python was sucessfully installed.

### How to install Python (Microsoft Windows)

### How to install Python (Linux)

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

### Install the Python Required Packages

To install the required Python packages inside the loaded/activated virtual enviroment run the following command:
```

```

## How to Build and Run
