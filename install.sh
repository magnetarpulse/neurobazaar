#!/bin/bash

# For Python 3.11
add-apt-repository ppa:deadsnakes/ppa

# Update and upgrade the system
apt update
apt upgrade

# For VTK and headless rendering
apt install g++-12 python3.11 python3.11-venv libpython3.11-dev build-essential cmake cmake-curses-gui mesa-common-dev mesa-utils libosmesa6-dev freeglut3-dev ninja-build 
update-alternatives --remove-all gcc
update-alternatives --remove-all g++
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 110
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120
update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 110
update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 120

# Check if the virtual environment already exists
if [ -d ".venv" ]; then
    echo "Error: The virtual environment '.venv' already exists. Please remove it or choose a different name."
    exit 1
fi

# Create a virtual environment
# Change the name of the virtual environment as needed
python3.11 -m venv .venv

# Activate the virtual environment
# If you changed the name of the virtual environment, make sure to change it here as well
source .venv/bin/activate

# Install VTK
git submodule init
git submodule update
mkdir build
cmake -GNinja -DCMAKE_INSTALL_PREFIX=.venv -DVTK_WRAP_PYTHON=ON -DVTK_SMP_IMPLEMENTATION_TYPE=STDThread -DVTK_USE_COCOA=OFF -DVTK_USE_X=OFF -DVTK_USE_WIN32_OPENGL=OFF -DVTK_OPENGL_HAS_OSMESA=ON -DVTK_OPENGL_USE_EGL=OFF -DVTK_DEFAULT_RENDER_WINDOW_OFFSCREEN=ON -DVTK_DEFAULT_RENDER_WINDOW_HEADLESS=ON -DVTK_GROUP_ENABLE_Web:STRING=WANT -S vtk/ -B build/
cmake --build build
cmake --build build --target install

# Upgrade pip
pip install --upgrade pip

# Install trame without dependencies
pip install --no-deps trame

# Install the rest of the dependencies from requirements.txt
pip install -r requirements.txt

# After all the dependencies, libraries and packages are installed, reboot the system
reboot