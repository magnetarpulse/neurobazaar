# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Rushikesh Rajendra Suryawanshi 2024 (rsuryawa@depaul.edu)
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)
- Areena Mahek 2024 (amahek@depaul.edu)
- Prem Kumar Gadwal 2024 (pgadwal@depaul.edu)
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

## Run The Installation Script

For simplicity, we have written a script that will automate the commands. Users will still require to give permission when installing required software and dependencies.


Enter the Neurobazaar directory if you have not yet already: ```cd neurobazaar```

For now (will update in production): ```git checkout demo```

Make the installation script an executable: ```chmod +x install.sh```

Run the script with sudo permission: ```sudo ./install.sh```

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