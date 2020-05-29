import os
from django.utils.timezone import activate
from re import compile
from .settings_var import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHORTLINK = "https://mhrt.ir"

AUTH_USER_MODEL = 'server.User'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'server',
    'mtadmin',
    'safedelete',
    'corsheaders',
    'debug_toolbar',
    'push_notifications',
    'django_celery_results',
    'django_celery_beat',
    'cloudinary',
    # 'django.contrib.admindocs',
    # 'django.contrib.postgres',
] + MY_INSTALLED_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.admindocs.middleware.XViewMiddleware', # docadmin
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'server.middleware.AuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

DISALLOWED_USER_AGENTS = [compile('PostmanRuntime')] if not DEBUG else []

# INTERNAL_IPS = [
#     '127.0.0.1',
# ]

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
    'x-csrf-token',
    'x-requested-with',
    'token',
    'admin',
]

CORS_EXPOSE_HEADERS = ['error']

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'


ROOT_URLCONF = 'mehr_takhfif.urls'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    # 'server.views.auth.Backend',
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

DATABASES = DATABASES

CACHES = CACHES
CACHE_TTL = 60 * 15
# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_ENGINE = "server.views.auth"  # custom session key
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

# TIME_ZONE = 'Iran'
# TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# activate(TIME_ZONE)



#     'version': 1,
#     'disable_existing_loggers': False,
#     'filters': {
#         'require_debug_false': {
#             '()': 'django.utils.log.RequireDebugFalse'
#         },
#         'require_debug_true': {
#             '()': 'django.utils.log.RequireDebugTrue'
#         }
#     },
#     'formatters': {
#         'verbose': {
#             'format': '{levelname}: {asctime}, {module}, {message}',
#             'style': '{'
#         },
#         'simple': {
#             'format': '{levelname} {message}',
#             'style': '{'
#         },
#     },
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#             'level': 'INFO',
#             'formatter': 'verbose'
#         },
#         'info_file': {
#             'level': 'INFO',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(BASE_DIR + '/logs/info', 'info.log'),
#             'formatter': 'verbose',
#             'when': 'D',
#             'backupCount': 30
#
#         },
#         'debug_file': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(BASE_DIR + '/logs/debug', 'debug.log'),
#             'formatter': 'verbose',
#             'when': 'D',
#             'backupCount': 30
#         },
#         'error_file': {
#             'level': 'ERROR',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(BASE_DIR + '/logs/error', 'error.log'),
#             'formatter': 'verbose',
#             'when': 'D',
#             'backupCount': 30
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console', 'info_file', 'debug_file', 'error_file'],
#             'level': 'DEBUG',
#             'propagate': True,
#         },
#     },
# }

if DEBUG:
    LOGGING = {}

TIME_ZONE = 'UTC'
USE_TZ = True
# CELERY_ENABLE_UTC = True
# CELERY_TIMEZONE = "UTC"

# Email settings
EMAIL_HOST = 'box.mehrtakhfif.com'
EMAIL_HOST_USER = 'superuser@mehrtakhfif.com'
EMAIL_HOST_PASSWORD = 'vcza$!me1jEnP%ES^0x2tWX&RehafiD'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
SERVER_EMAIL = 'api-traceback@mehrtakhfif.com'
ADMINS = [('Soheil', 'superuser@mehrtakhfif.com')]

# EMAIL_HOST = 'localhost'
# EMAIL_USE_TLS = False
# EMAIL_USE_SSL = False