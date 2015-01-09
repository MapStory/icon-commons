import os

DIRNAME = os.path.dirname(__file__)

SECRET_KEY = 'abc'

DEBUG = True
DATABASES = {
    'default' : {
        'ENGINE' : 'django.db.backends.sqlite3',
        'NAME' : os.path.join(DIRNAME, 'database.db'),
    }
}
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django_nose',
    'icon_commons',
    'taggit',
)
ROOT_URLCONF = 'icon_commons.urls'