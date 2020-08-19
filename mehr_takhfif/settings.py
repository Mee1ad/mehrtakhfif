import os
import sys
from re import compile

from django.utils.timezone import activate

from .settings_var import *

TESTING = 'test' in sys.argv

if TESTING:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHORTLINK = "https://mhrt.ir"

AUTH_USER_MODEL = 'server.User'
IPRESTRICT_GEOIP_ENABLED = False

INSTALLED_APPS = \
    [
        'jet.dashboard',
        'jet',
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
        # 'iprestrict',
        'django_user_agents',
        'django_seed',
        # 'cloudinary',
        # 'django.contrib.admindocs',
        # 'django.contrib.postgres',
        'prettyjson',
    ] + MY_INSTALLED_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'iprestrict.middleware.IPRestrictMiddleware',
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
    'django_user_agents.middleware.UserAgentMiddleware',
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

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'Iran'
TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# activate(TIME_ZONE)

# CELERY_ENABLE_UTC = True
# CELERY_TIMEZONE = "UTC"

USER_AGENTS_CACHE = 'default'

PUSH_NOTIFICATIONS_SETTINGS = {
    "FCM_API_KEY": "AAAAA21iJUs:APA91bHcTsXcWom96zJlUd6pokWud0zjPdo5lba5t2V_eh5s8ZoOtHTiuvya3NEBO73X3HOKJjnU57Mp_rRDWMW"
                   "iaN5uiKwQtWJqmpgUeB-SP48ObqUNU-_hX0OUmEU_wg_LIt-NQYHT",
    # "GCM_API_KEY": "AIzaSyAPoyIJc-tp_fCPafgnOsW8FzrLJjs9cIs",
    # "APNS_CERTIFICATE": "/path/to/your/certificate.pem",
    # "APNS_TOPIC": "com.example.push_test",
    # "WNS_PACKAGE_SECURITY_ID": "[your package security id, e.g: 'ms-app://e-3-4-6234...']",
    # "WNS_SECRET_KEY": "[your app secret key, e.g.: 'KDiejnLKDUWodsjmewuSZkk']",
    # "WP_PRIVATE_KEY": "/path/to/your/private.pem",
    # "WP_CLAIMS": {'sub': "mailto: development@example.com"}
}