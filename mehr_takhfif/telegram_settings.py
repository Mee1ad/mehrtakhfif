from django_telegram_login.widgets.constants import (SMALL, MEDIUM, LARGE, DISABLE_USER_PHOTO)
from django_telegram_login.widgets.generator import (create_callback_login_widget, create_redirect_login_widget)
from django_telegram_login.authentication import verify_telegram_authentication
from django_telegram_login.errors import (NotTelegramDataError, TelegramDataIsOutdatedError)

TELEGRAM_BOT_NAME = 'mhrtbot'
TELEGRAM_BOT_TOKEN = '1155951648:AAF71ubf6Y_GWt0vnbjvdTPIuhwA7aos-4E'
TELEGRAM_LOGIN_REDIRECT_URL = 'https://mehrtakhfif.com/tg_register'

telegram_login_widget = create_redirect_login_widget(
    TELEGRAM_LOGIN_REDIRECT_URL, TELEGRAM_BOT_NAME, size=LARGE, user_photo=DISABLE_USER_PHOTO
)
