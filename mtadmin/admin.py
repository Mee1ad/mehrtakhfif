from django.contrib import admin
from push_notifications.admin import GCMDeviceAdmin


# Register your models here.

GCMDeviceAdmin.ordering = ('-id',)
