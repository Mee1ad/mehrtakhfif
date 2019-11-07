import os
from django.utils.timezone import activate

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


SECRET_KEY = '#)@^eytrqed7)ka1qa0gcg$vx9&0ocru_xwqjlq%9e7baob_bn'
SALT = 'we\w[34=-otl34e[rl][qwe;w328474/*2342+-325(*^&%><>.'
TOKEN_SECRET = 'NRJu&@D-sqQa@2xEu6^yt8yjfd!*K4TawDD?v&LxChs2uJ7=9YvXF6pGEXNJHnPZ-gbHmnJf&D-9?y2g78YgKC?AX-FbHR6fgws_' \
               '&hGbAHuhE_TZh3yN?PGZky!Zx&uc'

DEBUG = True

ALLOWED_HOSTS = ['*']

HOST = 'http://192.168.1.95'
# HOST = 'http://192.168.137.95'
# HOST = 'http://192.168.137.1'
# HOST = 'http://mehrtakhfif.com'
# HOST = 'http://mt.com'

AUTH_USER_MODEL = 'server.User'

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
    'push_notifications'
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
    "http://mt.com:3000",
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

AUTHENTICATION_BACKENDS = [
    'server.views.auth.Backend',
    # 'django.contrib.auth.backends.ModelBackend',
]

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # 'ENGINE': 'django.db.backends.postgresql_psycopg2',
        # 'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'mehr_takhfif',
        # 'NAME': 'mehrtak1_db',
        'HOST': 'localhost',
        'USER': 'postgres',
        # 'USER': 'mehrtak1_admeen',
        'PASSWORD': 'admin',
        # 'PASSWORD': '_Rz*5g;mTFF*0#quq&',
        'port': '5432',
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "example"
    }
}
CACHE_TTL = 60 * 15
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# https://github.com/jazzband/django-push-notifications

PUSH_NOTIFICATIONS_SETTINGS = {
        "FCM_API_KEY": "[your api key]",
}


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Iran'

USE_I18N = True

USE_L10N = True

USE_TZ = False

activate(TIME_ZONE)


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'formatters': {
        'verbose': {
            'format': '{levelname}: {asctime}, {module}, {message}',
            'style': '{'
        },
        'simple': {
             'format': '{levelname} {message}',
             'style': '{'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'verbose'
        },
        'info_file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR + '/logs/info', 'info.log'),
            'formatter': 'verbose',
            'when': 'D',
            'backupCount': 30

        },
        'debug_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR + '/logs/debug', 'debug.log'),
            'formatter': 'verbose',
            'when': 'D',
            'backupCount': 30
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR + '/logs/error', 'error.log'),
            'formatter': 'verbose',
            'when': 'D',
            'backupCount': 30
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'info_file', 'debug_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

if DEBUG and os.environ.get('RUN_MAIN', None) != 'true':
    LOGGING = {}

if DEBUG == True:
    LOGGING = {}