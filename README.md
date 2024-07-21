# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)  
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

In order to run the Neurobazaar Platform you need to have at least Python **3.11** installed on your machine.

This software uses VTK version 9.3.1.

This software has been developed and tested with Python **3.11** on Ubuntu 22.04 LTS.

### Ubuntu Required Packages

You need to install the following packages:

```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt upgrade
sudo reboot
sudo apt install python3.11 python3.11-venv libpython3.11-dev build-essential g++-12 cmake cmake-curses-gui ninja-build mesa-common-dev mesa-utils libosmesa6-dev freeglut3-dev 
sudo update-alternatives --remove-all gcc
sudo update-alternatives --remove-all g++
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 110
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 110
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 120
```
I would reccomended upgrade the packages and then doing a reboot. Here is you can do it:
```
sudo apt upgrade
sudo reboot
```

### Python Virtual Environment Setup

All of the required Python packages are installed in a Python Virtual Environment. The first step is to create the virtual environment and the second step is to load/activate the environment. The first step has to be run only once.

Create the Python Virtual Environment on Ubuntu 22.04 LTS. It will be named .venv, but you can name it something else if you already have a virtual enviroment called .venv:  
```
python3.11 -m venv .venv
```

Load/activate the Python Virtual Environment in Ubuntu 22.04 LTS: 
```
source .venv/bin/activate
```

**If you already have a virtual enviroment installed and if you do not want to modify/use it, you can create a new one. As an example, if you already had a virtual envrioment called .vnev, the following commands will show you how to create a new virtual enviroment and activate it.**

```
python3.11 -m venv my-new-venv-but-you-can-name-it-whatever-you-want
```
To load/activate the new virtual enviroment, you would write the name of your new virtual enviroment after **source**. For me, I named my new virtual enviroment **"my-new-venv-but-you-can-name-it-whatever-you-want"**, but yours will be different if you named it different after the -m (flag/option): 

```
source my-new-venv-but-you-can-name-it-whatever-you-want/bin/activate
```

**To deactivate/get out of a virtual enviroment. In your terminal, just write the following command. Note: This will not delete the virtual enviroment, you can activate/enter it again by using the commands listed above.**

```
deactivate
```

**To delete the virtual enviroment. BE SUPER CAREFUL, THIS COMMAND IS IRREVERSIBLE. PLEASE UNDERSTAND THAT YOU CANNOT UNDO. IF YOU UNDERSTAND, REMOVE "you-have-read-me" from the command and press enter. AGAIN, THIS COMMAND IS IRREVERSIBLE AND YOU CANNOT UNDO IT ONCE YOU PRESS ENTER.**
<details>
    <summary>Click to reveal sensitive command</summary>

    
    you-have-read-me rm -rf my-new-venv-but-you-can-name-it-whatever-you-want
    

</details>

### VTK Setup

Before you can build VTK, you need to initalize the VTK submodule.

```
git submodule init
git submodule update
mkdir build
cmake -GNinja -DCMAKE_INSTALL_PREFIX=.venv -DVTK_WRAP_PYTHON=ON -DVTK_SMP_IMPLEMENTATION_TYPE=STDThread -DVTK_USE_COCOA=OFF -DVTK_USE_X=OFF -DVTK_USE_WIN32_OPENGL=OFF -DVTK_OPENGL_HAS_OSMESA=ON -DVTK_OPENGL_USE_EGL=OFF -DVTK_DEFAULT_RENDER_WINDOW_OFFSCREEN=ON -DVTK_DEFAULT_RENDER_WINDOW_HEADLESS=ON -DVTK_GROUP_ENABLE_Web:STRING=WANT -S vtk/ -B build/
cmake --build build
cmake --build build --target install
```

### Install node.js and npm
To be running the client of the visualization service(s) of the Neurobazaar platform, you will need to have **node.js version > 20.0.0** and **npm version>8.0.0**.

You can check if you have installed node.js and npm by the using the following commands. These commands will return the version of node.js and or npm is you have them installed. If nothing was returned, then you do not have node.js and or npm installed. If the command does return a version, but the version does not meet the requirments ( **node.js version > 20.0.0** and **npm>8.0.0**) then I would recommend updating node.js/npm. The next section shows how you can update node.js or npm.

```
node --version
npm --version
```
or

```
node -v
npm -v
```

**To install node.js and npm or if you want to update node.js and or npm, use the following the following commands.**

```
sudo apt install nodejs npm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
```

**You then need to close your command-line interface or exit from your remote machine if you are using a remote machine. After closing out, open/enter your command-line interface/remote machine again.** 

```
nvm install node
nvm use node
```

You should now have the latest node.js and npm version installed on your machine. You can verify if you have correctly installed node.js and npm and or verify if node.js/npm was updated by using the following commands

```
node --version
npm --version
```
or

```
node -v
npm -v
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