#!/bin/bash

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

# Upgrade pip
pip install --upgrade pip

# Install trame without dependencies
pip install --no-deps trame

# Install the rest of the dependencies from requirements.txt
pip install -r requirements.txt