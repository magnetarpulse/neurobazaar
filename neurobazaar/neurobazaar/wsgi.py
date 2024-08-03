"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

<<<<<<<< HEAD:neurobazaar/neurobazaar/wsgi.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurobazaar.settings')
========
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
>>>>>>>> f982d483fbb1d12cb88d0beb63b0d325d0b951fb:neurobazaar/backend/backend/wsgi.py

application = get_wsgi_application()
