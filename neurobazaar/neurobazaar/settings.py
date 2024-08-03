"""
Django settings for neurobazaar project.

Generated by 'django-admin startproject' using Django 5.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

# ----------------------------
# Change detected: import os |
# ----------------------------
import os                  
# ----------------------------
# End of change detected     |
# ----------------------------
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------
# Change detected: Set the variable BASE_DIRR                         |
# ---------------------------------------------------------------------
BASE_DIRR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ---------------------------------------------------------------------
# End of change detected                                              |
# ---------------------------------------------------------------------

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-i9=ybhwb)z5es$kipg(+h(fk1vf0wwh(ep4=*6#u#&y4trgsls'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'home.apps.HomeConfig', # Change detected: ___ -> 'home.apps.HomeConfig'   
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_vite', # Change detected: ___ -> 'django_vite'  
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'neurobazaar.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")], # Change detected: 'DIRS': [], -> 'DIRS': [os.path.join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'neurobazaar.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'), # Change detected: 'NAME': BASE_DIR / 'db.sqlite3', -> 'NAME': os.path.join(BASE_DIRR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

LOGIN_URL = '/login_register' # Change detected: ___ -> LOGIN_URL = '/login_register'

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------------------------------------------------------------------------------
# Changes detected: Setting up Django Vite                                                                                            |
# -------------------------------------------------------------------------------------------------------------------------------------

# Where ViteJS assets are built.
DJANGO_VITE_ASSETS_PATH = BASE_DIR / "vue-app" / "dist"

# If use HMR or not.
DJANGO_VITE_DEV_MODE = DEBUG

# Name of static files folder (after running the command "python manage.py collectstatic").
STATIC_ROOT = BASE_DIR / "collectedstatic"

DJANGO_VITE_MANIFEST_PATH = BASE_DIR / 'vue-app' / 'dist' / '.vite' / 'manifest.json'

DJANGO_VITE_DEV_SERVER_URL = 'http://localhost:5173/'

# Include DJANGO_VITE_ASSETS_PATH into STATICFILES_DIRS to be copied inside when running the command "python manage.py collectstatic".
# Include both DJANGO_VITE_ASSETS_PATH and STATIC folder into STATICFILES_DIRS.
STATICFILES_DIRS = [
    DJANGO_VITE_ASSETS_PATH,
    os.path.join(BASE_DIRR, "static")  # Add this line to include the STATIC folder
]

# -------------------------------------------------------------------------------------------------------------------------------------
# End of setting up Django Vite. No more changes detected.                                                                            |
# -------------------------------------------------------------------------------------------------------------------------------------