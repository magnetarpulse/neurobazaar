# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Vivek Shravan Gupta 2024 (vgupta16@depaul.edu)  
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)  

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Requirements and Setup

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

```
source .venv/bin/activate
```

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

```
python -m pip install -r requirements.txt
```

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

## How to Build and Run the Neurobazaar (Development Mode)
Most likely, if you closed your command-line interface or exited from your remote machine, once you open/connect to your command-line interface/remote machine again, you will no longer be in the Python Virtual Environment. 

Please make sure you are in the Python Virtual Environment.

You can activate your Python Virtual Environment from the following command (if you did not name your Python Virtual Environment "**`.venv`**", then it will be the name of your Python Virtual Environment): 

```
source .venv/bin/activate
```

Before anything, since this is development mode, you will need to rename **`workspaces.html`**. You can rename it to whatever you want, just make sure that the it is no longer **`workspaces.html`**.

Change directory to the **`templates`** directory.

```
cd path/to/neurobazaar/neurobazaar/templates/workspace.html
```

Rename **`workspaces.html`** to **`new_name.html`**.

```
mv workspaces.html new_name.html
```

Then you will need to rename **`workspaces_development_only.html`** to **`workspaces.html`**.

**Note:** It **must** be renamed to **`workspaces.html`** if you do not want to break the current django server. However, if you plan to modify the django server, then you can name it to whatever you want, just make sure to change **`home/views.py`**.

```
mv workspaces_development_only.html workspaces.html
```

Once finished renaming the **`workspaces.html`** and **`workspaces_development_only.html`**, please change directory and enter the **`trame-server-examples`** directory.

```
cd path/to/neurobazaar/neurobazaar/trame-server-examples
```

Please start the trame-server.

```
python trame_server_example.py --server
```

In a **new** terminal, please change directory to **`trame-client-examples`**.

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

```
npm run dev
```

In a **new** terminal, please change directory to neurobazaar/neurobazaar.

```
cd path/to/neurobazaar/neurobazaar
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

## How to Build and Run the Neurobazaar (Production Mode)
Most likely, if you closed your command-line interface or exited from your remote machine, once you open/connect to your command-line interface/remote machine again, you will no longer be in the Python Virtual Environment. 

Please make sure you are in the Python Virtual Environment.

You can activate your Python Virtual Environment from the following command (if you did not name your Python Virtual Environment "**`.venv`**", then it will be the name of your Python Virtual Environment): 

```
source .venv/bin/activate
```

Once activated, please change directory and enter the **`trame-client-examples`** directory.

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

After installing and bundling, in a **new** terminal, please change directory to **`neurobazaar`**. You will also need to be in the Python Virtual Environment

```
source .venv/bin/activate
cd path/to/neurobazaar/neurobazaar
```

We need to create new migrations and apply these migrations.

**Note:** If you receive an unexpected error(s) or warning(s) while creating new migrations or applying these migrations, please refer to the **Other Information** section. If you do not see the error(s) or warning(s) list in the  **Other Information** section, please contact one of the contributors or maintainers to receive help. 

```
python manage.py makemigrations home
python manage.py migrate
```

After creating new migrations or applying these migrations, we need to collect all the static files.

```
python manage.py collectstatic
```

After running the command, a new directory called **`collectedstatic`** will be created. We need to change directory to this **`collectedstatic`** directory.

```
cd/path/to/neurobazaar/collectedstatic
```

We need to find and copy two pieces of information; the bundled Vue.js Javascript (**`.js`**) and the bundled Vue.js Cascading Style Sheets (**`.css`**).

Please list the files of the **`collectedstatic`** directory.

```
ls
```

You should see two files, they both start with **`main-`** and one of the files should end with **`.js`** and the other ends with **`.css`**. Please write write down the full name of the two files.

In my case, my files are called:

```
main-DYg20UMC.js
main-B7nC34Ax.css
```

After writing down the full names of the two files. Please change directory to the **`templates`** directory.

You will need to directly edit the **`workspaces.html`**. 

Open the file using nano.

**Note:** If you have an editor, this would be a lot simpler for you.

```
nano workspaces.html
```

Using the nano text editor, please change the following **`main-DYg20UMC.js`** and **`main-B7nC34Ax.css`** to the names of your file.

Here is how it looks for me, but it will be different for you:

```

<!-- Load the CSS file -->
<link rel="stylesheet" href="{% static 'main-B7nC34Ax.css' %}">

...

        <!-- Dynamic workspace content -->
        <div id="workspaceContent">
            <!-- Each workspace tab content -->
            <div class="tab-content">
                <!-- Placeholder for initial workspace content -->
            </div>
        </div>
        
        <script src="{% static 'main-DYg20UMC.js' %}"></script>
```

After making the changes, save the changes:

```
^0
^X
```

After that, please change directory to **`trame-server-examples`**.

```
cd path/to/neurobazaar/neurobazaar/trame-server-examples
```

Start the trame server

```
python trame_server_example.py --server
```

In a **new** terminal, change directory to **`neurobazaar`**. You will also need to be in the Python Virtual Environment. 

```
source .venv/bin/activate
cd path/to/neurobazaar/neurobazaar
```

Start the django server.

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