#!/usr/bin/env python

import glob
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

# our install script puts dependencies here
sys.path.insert(0, os.path.join(BASE_DIR, "libs"))
# sdk is not a proper python package
sys.path.insert(0, os.path.join(BASE_DIR, "libs", "google_appengine"))

import django
from django.conf import settings

# Unfortunately, apps can not be installed via ``modify_settings``
# decorator, because it would miss the database setup.
CUSTOM_INSTALLED_APPS = (
    'fluent',
    'django.contrib.admin',
)

ALWAYS_INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

ALWAYS_MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


settings.configure(
    TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True}],
    SECRET_KEY = "django_tests_secret_key",
    DEBUG = False,
    TEMPLATE_DEBUG = False,
    ALLOWED_HOSTS = [],
    INSTALLED_APPS = ALWAYS_INSTALLED_APPS + CUSTOM_INSTALLED_APPS,
    MIDDLEWARE_CLASSES = ALWAYS_MIDDLEWARE_CLASSES,
    ROOT_URLCONF = 'tests.urls',
    DATABASES = {
        'default': {
            'ENGINE': 'djangae.db.backends.appengine',
        }
    },
    LANGUAGE_CODE = 'en-us',
    TIME_ZONE = 'UTC',
    USE_I18N = True,
    USE_L10N = True,
    USE_TZ = True,
    STATIC_URL = '/static/',
    # Use a fast hasher to speed up tests.
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ),
    FIXTURE_DIRS = glob.glob(BASE_DIR + 'fluent/' + '*/fixtures/')
)

os.environ["DJANGAE_APP_YAML_LOCATION"] = os.path.join(BASE_DIR, "fluent")

args = [sys.argv[0], 'test']

# Current module (``tests``) and its submodules.
test_cases = '.'

# Allow accessing test options from the command line.
offset = 1
try:
    sys.argv[1]
except IndexError:
    pass
else:
    option = sys.argv[1].startswith('-')
    if not option:
        test_cases = sys.argv[1]
        offset = 2

args.append(test_cases)
# ``verbosity`` can be overwritten from command line.
args.append('--verbosity=2')
args.extend(sys.argv[offset:])

from djangae.core.management import execute_from_command_line

execute_from_command_line(args)
