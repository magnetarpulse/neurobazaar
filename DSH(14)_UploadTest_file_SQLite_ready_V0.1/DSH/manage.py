#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    print("test")
    DB_choice_by_user = input('enter the database you want to start in:\n')     
    print(DB_choice_by_user) 
    
    if(DB_choice_by_user=='sqlite3'):
        os.environ['Django_DB_Choice']='sqlite3'
    elif DB_choice_by_user == 'postgresql':
        os.environ['Django_DB_Choice']='postgresql'
    else:
        print("wrong choice, using default SQLite3 database")
        os.environ['Django_DB_Choice']='sqlite3'
            
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DSH.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
