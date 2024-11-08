@echo off

:: Check if the virtual environment already exists
if exist ".venv" (
    echo Error: The virtual environment '.venv' already exists. Please remove it or choose a different name.
    exit /b 1
)

:: Create a virtual environment
python -m venv .venv

:: Activate the virtual environment
call .venv\Scripts\activate

:: Upgrade pip
pip install --upgrade pip

:: Install trame without dependencies
pip install --no-deps trame

:: Install the rest of the dependencies from requirements.txt
pip install -r requirements.txt

:: The virtual environment remains activated