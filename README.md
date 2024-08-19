# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

In order to run the Neurobazaar Platform you need to have Python **3.11** and Node.js **v22.5** installed on your computer.

This software uses VTK version **9.3.1**.

This software has been developed and tested on Ubuntu **22.04 LTS**.

### Ubuntu Required Packages

To install and manage Node.js installations you can use Node Version Manager. Use the following link to install the latest version of NVM:
https://github.com/nvm-sh/nvm

You need to install the following packages:

```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install g++-12 python3.11 python3.11-venv libpython3.11-dev build-essential cmake cmake-curses-gui mesa-common-dev mesa-utils libosmesa6-dev freeglut3-dev ninja-build 
sudo update-alternatives --remove-all gcc
sudo update-alternatives --remove-all g++
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 110
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 110
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 120
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

### VTK Setup

Before you can build VTK, you need to initalize the VTK submodule.

```
git submodule init
git submodule update
mkdir build
cmake -GNinja -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DVTK_WRAP_PYTHON=ON -DVTK_SMP_IMPLEMENTATION_TYPE=STDThread -DVTK_USE_COCOA=OFF -DVTK_USE_X=OFF -DVTK_USE_WIN32_OPENGL=OFF -DVTK_OPENGL_HAS_OSMESA=ON -DVTK_OPENGL_USE_EGL=OFF -DVTK_DEFAULT_RENDER_WINDOW_OFFSCREEN=ON -DVTK_DEFAULT_RENDER_WINDOW_HEADLESS=ON -DVTK_GROUP_ENABLE_Web:STRING=WANT -S vtk/ -B build/
cmake --build build
cmake --build build --target install
```

### Install the Python Dependencies/Packages

Install the dependecies/packages on the loaded/activated virtual environment:
```
python -m pip install -r requirements.txt
```

## How to Build and Run

Migrate the Django database (only required to run once or when the models have been changed):
```
python manage.py makemigrations home
```
```
python manage.py migrate
```

Install the Node.js packages (only required to run once or when the Javascript/Vue applications change):
```
npm install
```

Build the static Javascript frontend code (only required to run once or when the Javascript/Vue applications change):
```
npm run build
```

Start the Trame server:
```
python trame/server.py --server
```

If running in development mode start the Node.js server (do not run this command if running server in production mode):
```
npm run dev
```

Start the server to access the Neurobazaar Platform locally:
```
python manage.py runserver
```
