# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)
- Areena Mahek 2024 (amahek@depaul.edu)

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

In order to run the Neurobazaar Platform you need to have at least Python **3.11** installed on your computer.

For Windows 10 this software has been tested with Python **3.11.5**.

### Ubuntu Required Packages

Please install Deadsnakes Personal Package Archive (PPA) to install Python **3.11** or newer on your machine.

**Note:** If you are using a newer Ubuntu version, and Python **3.11** or newer is available in the official Ubuntu repositories, then you will not need to install Deadsnakes Personal Package Archive (PPA).
```
sudo add-apt-repository ppa:deadsnakes/ppa
```

After, installing the Deadsnakes Personal Package Archive (PPA), I would recommend check if your system has any available updates, installing any necessary upgrades and then doing a reboot of the system.

```
sudo apt update
sudo apt upgrade
sudo reboot
```
After rebooting. You will also need to install these packages if you want to run the Neurobazaar from a headless machine.

**Note:** If you plan to build the Neurobazaar on your local machine and or a headed machine, then you will not need to install these packages. However, I would not recommend the Neurobazaar on your local machine because of the architecture of the Neurobazaar. 

```
sudo apt install python3.11 python3.11-venv libpython3.11-dev build-essential g++-12 cmake cmake-curses-gui ninja-build mesa-common-dev mesa-utils libosmesa6-dev freeglut3-dev 
sudo update-alternatives --remove-all gcc
sudo update-alternatives --remove-all g++
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 110
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 110
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 120
```


### Set up the Python Virtual Environment for Windows

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
or
.venv/Scripts/activate
```

### Python Virtual Environment Setup for Ubuntu/Linux

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
pip install "dask<2025"
python -m pip install -r requirements.txt
```
The media folder should have all the datasets, includes the max_slices folder, LIDC original folder, Max_Slices_OoD.csv, All_slices.csv
### Export media into media folder
```
sudo apt install unzip
cd media
unzip lidc_pixConvImg.zip
```

### Download pre-downloaded dicom images with contors from the link below:
https://drive.google.com/file/d/1QtvgV8sX0h-nxjZNemYMnfnOQcs5K_p_/view?usp=sharing

### When downloaded 
```
cd media
unzip dicom_images.zip   
```

### Make Migrations and migrate
```
python manage.py makemigrations
python manage.py migrate
```

### Start the Django Server

```
python manage.py runserver 0.0.0.0:8000
```

### Start the Trame Server with the python Code

```
python dask_working_code.py
```

The browser opens with the localhost:port with the interface running.

### If required to run on a different machine, run the django server and start the trame server. In the browser:

```
http://server_ip:port/
```



