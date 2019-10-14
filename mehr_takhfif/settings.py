"""
Django settings for mehr_takhfif project.

Generated by 'django-admin startproject' using Django 2.2.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from django.utils.timezone import activate


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# GEOS_LIBRARY_PATH = 'C:\\OSGeo4W64\\bin\\geos_c.dll'
# GDAL_LIBRARY_PATH = 'C:\\OSGeo4W64\\bin\\gdal201.dll'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '#)@^eytrqed7)ka1qa0gcg$vx9&0ocru_xwqjlq%9e7baob_bn'
SALT = 'we\w[34=-otl34e[rl][qwe;w328474/*2342+-325(*^&%><>.'
# noinspection SpellCheckingInspection
TOKEN_SECRET = 'NRJu&@D-sqQa@2xEu6^yt8yjfd!*K4TawDD?v&LxChs2uJ7=9YvXF6pGEXNJHnPZ-gbHmnJf&D-9?y2g78YgKC?AX-FbHR6fgws_' \
               '&hGbAHuhE_TZh3yN?PGZky!Zx&uc'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

HOST = 'http://192.168.1.95'
# HOST = 'http://192.168.137.95'
# HOST = 'http://192.168.137.1'

AUTH_USER_MODEL = 'server.User'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'server',
    'safedelete',
    'corsheaders',
    'debug_toolbar',
    'mehrpeyk',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'server.middleware.AuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = [
    '127.0.0.1',
]

CORS_ORIGIN_WHITELIST = [
    "http://192.168.1.96:3000",
    "http://192.168.43.96:3000",
    "http://localhost:3000",
    "http://192.168.1.95",
    "http://mt.com",
    "http://mt.com:3000"
]
# CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'


ROOT_URLCONF = 'mehr_takhfif.urls'

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
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

WSGI_APPLICATION = 'mehr_takhfif.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # 'ENGINE': 'django.db.backends.postgresql_psycopg2',
        # 'ENGINE': 'django.contrib.gis.db.backends.postgis',
        # 'NAME': 'mehr_takhfif',
        'NAME': 'mehrtak1_db',
        'HOST': 'localhost',
        # 'USER': 'postgres',
        'USER': 'mehrtak1_admeen',
        # 'PASSWORD': 'admin',
        'PASSWORD': '_Rz*5g;mTFF*0#quq&',
        'port': '5432',
    }
}

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379/1",
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient"
#         },
#         "KEY_PREFIX": "example"
#     }
# }
CACHE_TTL = 60 * 15
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Iran'

USE_I18N = True

USE_L10N = True

USE_TZ = False

activate(TIME_ZONE)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

if DEBUG and os.environ.get('RUN_MAIN', None) != 'true':
    LOGGING = {}
