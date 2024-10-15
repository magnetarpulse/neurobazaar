#!/usr/bin/env python
import os
import sys
import hupper

def run_daphne(host, port):
    from daphne.server import Server
    from daphne.endpoints import build_endpoint_description_strings
    from neurobazaar.asgi import application  # Import your ASGI application

    endpoints = build_endpoint_description_strings(host=host, port=port)
    Server(application, endpoints=endpoints).run()

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurobazaar.settings")
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

    # Check if the command is to run the server
    if sys.argv[1:2] == ['runserver']:
        # Default values
        host = '127.0.0.1'
        port = 8000

        # Parse host and port if provided
        if len(sys.argv) > 2:
            addr = sys.argv[2]
            if ':' in addr:
                host, port = addr.split(':')
                port = int(port)
            else:
                port = int(addr)

        # Start the reloader
        reloader = hupper.start_reloader('manage.run_daphne', worker_kwargs={'host': host, 'port': port})
        
        print(f"Starting development server at http://{host}:{port}/")
        print("Quit the server with CONTROL-C.")

        # Run Daphne (this will be called by hupper in a separate process)
        run_daphne(host, port)
    else:
        execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
