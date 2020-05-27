from django.core.exceptions import ValidationError


class ActivationError(Exception):
    pass


class WarningMessage(Exception):
    pass
