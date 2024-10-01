# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Rushikesh Suryawanshi 2024 (rsuryawa@depaul.edu)
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)
- Areena Mahek 2024 (amahek@depaul.edu)
- Prem Gadwal 2024 (pgadwal@depaul.edu)
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  

Powered by:
- Chameleon Cloud 2024

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

**Note:** This software has been developed, tested and ran with Python **3.11** on a bare metal (headless) Ubuntu 22.04 LTS machine provided by the Chameleon Cloud. 

In order to run the Neurobazaar Platform, it is recommended to have Python **3.11** installed on your machine. The Neurobazaar team has not tested the software using an older Python version. It is as likely that it could or could not work on an older Python version. If you try running the Neurobazaar on an older Python version, please let us know the results.

This software uses VTK version **9.3.1**.

If you are running the Neurobazaar and its components on a headless machine, you need to initialize, set up and build VTK manually (instructions below). This is primarily how the Neurobazaar team is running and developing the Neurobazaar.

If you are not running the Neurobazaar and its components on a headless machine, you do not have to install and set up VTK manually. Instead, you can install the distributed VTK package (wheels). You can do so using the command ```pip install vtk```.

### Ubuntu Required Packages

You need to install the following packages (assuming Ubuntu22.04 LTS and Python **3.11**):
```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt upgrade
sudo apt install g++-12 python3.11 python3.11-venv libpython3.11-dev build-essential cmake cmake-curses-gui mesa-common-dev mesa-utils libosmesa6-dev freeglut3-dev ninja-build 
sudo update-alternatives --remove-all gcc
sudo update-alternatives --remove-all g++
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 110
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 110
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 120
sudo reboot
```

**Note:** ```sudo reboot``` will take approximately 3 minutes to 5 minutes.

### Python Virtual Environment Setup

All of the required Python dependencies/packages/wheels are installed in a Python virtual environment (assuming Python **3.11**). The first step is to create the virtual environment and the second step is to activate the virtual environment. The first step has to be run only once.

Create the Python virtual environment on Ubuntu 22.04 LTS:  
```
python3.11 -m venv .venv
```

Activate the Python virtual environment on Ubuntu 22.04 LTS: 
```
source .venv/bin/activate
```

### VTK Setup

If you are running the Neurobazaar on a headless machine. You will need to initialize, set up and build VTK manually. Here are the commands:
```
git submodule init
git submodule update
mkdir build
cmake -GNinja -DCMAKE_INSTALL_PREFIX=.venv -DVTK_WRAP_PYTHON=ON -DVTK_SMP_IMPLEMENTATION_TYPE=STDThread -DVTK_USE_COCOA=OFF -DVTK_USE_X=OFF -DVTK_USE_WIN32_OPENGL=OFF -DVTK_OPENGL_HAS_OSMESA=ON -DVTK_OPENGL_USE_EGL=OFF -DVTK_DEFAULT_RENDER_WINDOW_OFFSCREEN=ON -DVTK_DEFAULT_RENDER_WINDOW_HEADLESS=ON -DVTK_GROUP_ENABLE_Web:STRING=WANT -S vtk/ -B build/
cmake --build build
cmake --build build --target install
```

**Note:** The amount of time it takes to initialize, set up and build VTK varies depending on the machine. It could take 10 minutes, or it could take 3 hours, it really depends on the machine.

### Install the Python Dependencies/Packages/Wheels

Install the dependencies/packages/wheels in the activated virtual environment:
```
python -m pip install -r requirements.txt
```

## How to Build and Run the Neurobazaar

Before starting the server, ensure that the Django database is correctly set up by performing migrations and creating a superuser for administrative access. Follow these steps (inside the activated virtual environment):

1. **Prepare Database Migrations**:  
   Initialize database migrations needed for the Django models:
```
python manage.py makemigrations
```

2. **Apply Migrations**:  
Apply the prepared migrations to the database:
```
python manage.py migrate
```

3. **Create Superuser**:  
Create an administrative user to access the Django admin panel:
```
python manage.py createsuperuser
```

When prompted:
- Username: `any_username` (choose any username you prefer)
- Email Address: (can be left blank)
- Password: `add_your_password` (enter a password of your choice)
- Confirm the password by re-entering it. If prompted, you can press 'y' to bypass password validation, or re-enter the password if you prefer not to bypass.

4. **Start the Django Server**:  
Start the server to access the Neurobazaar Platform locally:
```
python manage.py runserver
```