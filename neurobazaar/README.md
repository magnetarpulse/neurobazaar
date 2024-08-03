# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  
<<<<<<< HEAD
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)  
=======
>>>>>>> f982d483fbb1d12cb88d0beb63b0d325d0b951fb

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

<<<<<<< HEAD
In order to run the Neurobazaar Platform you need to have at least Python **3.11** installed on your machine.

This software uses VTK version 9.3.1.

This software has been developed and tested with Python **3.11** on Ubuntu 22.04 LTS.

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

### Python Virtual Environment Setup

All of the required Python packages are installed in a Python Virtual Environment. The first step is to create the virtual environment and the second step is to load/activate the environment. The first command has to be run only once.

To create the Python Virtual Environment on Ubuntu 22.04 LTS or a newer Ubuntu version, run the following commands. 

**Note:** In this example, we are naming our Python Virtual Environment "**.venv**", but you can name it something else if you already have a Python Virtual Environment called .venv:  

```
python3.11 -m venv .venv
```

To load/activate the Python Virtual Environment on Ubuntu 22.04 LTS or a newer Ubuntu version: 

=======
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
>>>>>>> f982d483fbb1d12cb88d0beb63b0d325d0b951fb
```
source .venv/bin/activate
```

<<<<<<< HEAD
### VTK Setup

**Note:** If you are not building the Neurobazaar on a headless machine and did not install the "**Ubuntu Required Packages**", then you will **not** need to run the following commands. 

Before you can build VTK, you need to initialize the VTK submodule.

```
git submodule init
git submodule update
```

After initializing the VTK submodule, we need to create a new directory named "**build**". This directory will contain the VTK built from source.
```
mkdir build
```

To build VTK, run the following commands. 

**Note:** The speed of building VTK will vary depending on the machine. It could take minutes to hours depending on the machine.
```
cmake -GNinja -DCMAKE_INSTALL_PREFIX=.venv -DVTK_WRAP_PYTHON=ON -DVTK_SMP_IMPLEMENTATION_TYPE=STDThread -DVTK_USE_COCOA=OFF -DVTK_USE_X=OFF -DVTK_USE_WIN32_OPENGL=OFF -DVTK_OPENGL_HAS_OSMESA=ON -DVTK_OPENGL_USE_EGL=OFF -DVTK_DEFAULT_RENDER_WINDOW_OFFSCREEN=ON -DVTK_DEFAULT_RENDER_WINDOW_HEADLESS=ON -DVTK_GROUP_ENABLE_Web:STRING=WANT -S vtk/ -B build/
cmake --build build
cmake --build build --target install
```

### Install the Python Dependencies/Packages

Install the dependencies/packages on the loaded/activated virtual environment:

=======
### Install the Python Dependencies/Packages

Install the dependecies/packages on the loaded/activated virtual environment:
>>>>>>> f982d483fbb1d12cb88d0beb63b0d325d0b951fb
```
python -m pip install -r requirements.txt
```

<<<<<<< HEAD
**Note:** If you are not building the Neurobazaar on a headless machine and did not install the "**Ubuntu Required Packages**", then please install run the following command:

```
python -m pip install -r not_headless_requirements.txt
```

### Install node.js and npm
To run the client of the visualization service(s) of the Neurobazaar platform, you will need to have **node.js version > 20.0.0** and **npm version>8.0.0**.

You can check if you have installed node.js and npm by the using the following commands. These commands will return the version of node.js and or npm is you have them installed. If nothing was returned, then you do not have node.js and or npm installed. If the command does return a version, but the version does not meet the requirements ( **node.js version > 20.0.0** and **npm>8.0.0**) then I would recommend updating node.js/npm. The next section shows how you can update node.js or npm.

```
node --version
npm --version
```

To install node.js and npm or if you want to update node.js and or npm, use the following the following commands.

```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
```

You then need to close your command-line interface or exit from your remote machine (if you are using a remote machine). After closing/exiting out, open/connect to your command-line interface/remote machine again.

```
nvm install node
nvm use node
```

You should now have the latest node.js and npm version installed on your machine. You can verify if you have correctly installed node.js and npm and or verify if node.js/npm was updated by using the following commands

```
node --version
npm --version
```

## How to Build and Run the Neurobazaar
Most likely, if you closed your command-line interface or exited from your remote machine, once you open/connect to your command-line interface/remote machine again, you will no longer be in the Python Virtual Environment. 

Please make sure you are in the Python Virtual Environment.

You can activate your Python Virtual Environment from the following command (if you did not name your Python Virtual Environment "**.venv**", then it will be the name of your Python Virtual Environment): 

```
source .venv/bin/activate
```

Once activated, please change directory and enter the **trame-server-examples** directory.

```
cd path/to/neurobazaar/neurobazaar/trame-server-examples
```

Please start the trame-server

```
python trame_server_example.py --server
```

In a **new** terminal, please change directory to neurobazaar/neurobazaar/trame-client-examples.

```
cd path/to/neurobazaar/neurobazaar/trame-client-examples
```

We need to install the dependencies of the client of the visualization service(s) of the Neurobazaar platform. 

**Note:** If you receive an unexpected error(s) or warning(s) while installing the dependencies, please refer to the **Other Information** section. If you do not see the error(s) or warning(s) list in the  **Other Information** section, please contact one of the contributors or maintainers to receive help. 

```
npm install
```

We then need to bundle the client of the visualization service(s) of the Neurobazaar platform. 

```
npm run build
```

We then need to start the server of the client of the visualization service(s) of the Neurobazaar platform. 

**Note:** This command is only for development purposes, this command will no longer need to be ran in the future.

=======
## How to Build and Run

Make Migration for the Django database (only required to run once):
```
cd backend   
```
```
python manage.py makemigrations home
```

Migrate the Django database (only required to run once):
```
python manage.py migrate
```

Start the Vue & Vite server(In different terminal):
```
cd trame  
```
Install npm (once at the beginning)
```
npm install
```
>>>>>>> f982d483fbb1d12cb88d0beb63b0d325d0b951fb
```
npm run dev
```

<<<<<<< HEAD
In a **new** terminal, please change directory to neurobazaar/neurobazaar.

```
cd path/to/neurobazaar/neurobazaar.
```

We need to create new migrations and apply these migrations.

**Note:** If you receive an unexpected error(s) or warning(s) while creating new migrations or applying these migrations, please refer to the **Other Information** section. If you do not see the error(s) or warning(s) list in the  **Other Information** section, please contact one of the contributors or maintainers to receive help. 
```
python manage.py makemigrations home
python manage.py migrate
```

Finally, start the Neurobazaar server.

```
python manage.py runserver   
```

### Other Information

#### Want to Build Your Own?
The visualization service(s) (trame-client, trame-server) has been cleaned up in this `neurobazaar` directory. This means that there is almost no comments. This is only a verification and an example to the developers and maintainers of this platform. **Please do not take this code as a basis for building your own visualization service(s)**. The developers and maintainers who this is meant for will have a better understanding of the code, which is why it has been cleaned. But if you are trying to build your own example, there is a lot better examples. **Please refer to the `example` directory. The `example` directory will contain better examples since it has not been cleaned (there are comments).**

#### Warning(s) or Error(s) encountered
We are aware of these warnings and or errors. Please ignore this warnings if you receive it, these warnings should be resolved soon. If you are experiencing or receive a warning or error that is not listed here, please contact one of the contributors or maintainers of this platform to receive help.

Warning one (**not fatal/still passing**):
```
npm warn deprecated inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
```
Warning two (**not fatal/still passing**):
```
npm warn deprecated glob@7.2.3: Glob versions prior to v9 are no longer supported
```
Warning three (**not fatal/still passing**):
```
?: (staticfiles.W004) The directory '/neurobazaar/neurobazaar/vue-app/dist' in the STATICFILES_DIRS setting does not exist.
No changes detected in app 'home'
```
=======
Start the Django server(In different terminal):
```
cd backend   
```
```
python manage.py runserver   
```
>>>>>>> f982d483fbb1d12cb88d0beb63b0d325d0b951fb
