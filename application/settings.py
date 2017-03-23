from __future__ import absolute_import, unicode_literals
"""
Django settings for catalystinnovation project.

Generated by 'django-admin startproject' using Django 1.10.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_secret_file(secret_file_path, default=None):
    data = default
    if secret_file_path:
        with open(secret_file_path, 'rt') as f:
            data = f.read().strip()
    return data



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = read_secret_file(os.environ.get('DJANGO_SECRET_KEY_FILE'),
                              '-gd#qi9!+)u+!65m)m^ad)yq2b5)jbny)(&8lzp-m5$+2z%78%')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '192.168.99.1',
    '0.0.0.0',
    '150.242.40.210',
    '150.242.40.216',
    '150.242.40.218',
    '150.242.40.212',
]


# Application definition

INSTALLED_APPS = [
    'domain_api.apps.DomainApiConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_nose',
    'rest_framework_swagger',
    'django_celery_results',
    'raven.contrib.django.raven_compat',
]
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'application.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'application.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

RAVEN_CONFIG = {
    'dsn': read_secret_file(os.environ.get('SENTRY_DSN_FILE', None),
                            os.environ.get('SENTRY_DSN', None)),
    'environment': os.environ.get('SENTRY_ENVIRONMENT', None)
}
JWT_AUTH = {
    "JWT_ALLOW_REFRESH": True,
    "JWT_SECRET_KEY": read_secret_file(os.environ.get("JWT_SECRET_KEY_FILE"),
                                       SECRET_KEY),
    "JWT_EXPIRATION_DELTA": datetime.timedelta(
        seconds=int(os.environ.get('JWT_EXPIRATION_DELTA_SECONDS', 300))
    ),
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': read_secret_file(os.environ.get('MYSQL_DATABASE_FILE', None),
                                 os.environ.get("MYSQL_DATABASE", 'domaindb')),
        'USER': read_secret_file(os.environ.get('MYSQL_USER_FILE', None),
                                 os.environ.get("MYSQL_USER", 'mysqluser')),
        'PASSWORD': read_secret_file(os.environ.get('MYSQL_PASSWORD_FILE',
                                                    None),
                                     os.environ.get("MYSQL_PASSWORD", '')),
        'HOST': os.environ.get("MYSQL_HOST", '127.0.0.1'),
        'PORT': os.environ.get("MYSQL_PORT", 3306)
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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

DJANGO_LOGGING = {
    "CONSOLE_LOG": True,
    "LOGLEVEL": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    "CONTENT_JSON_ONLY": True

}


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/hour',
        'user': '1000/day'
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'memcached:11211',
    }
}

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT', 5672)
RABBITMQ_USER = os.environ.get('RABBITMQ_DEFAULT_USER', 'guest')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_DEFAULT_PASS', 'guest')
RABBITMQ_VHOST = os.environ.get('RABBITMQ_DEFAULT_VHOST', '/')
CELERY_BROKER_URL = 'amqp://' + RABBITMQ_USER + ':' + RABBITMQ_PASSWORD + '@' + RABBITMQ_HOST + '/' + RABBITMQ_VHOST
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_RESULT_BACKEND = 'rpc://'
