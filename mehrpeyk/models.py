from django.db import models
from server.models import Factor
from safedelete.models import SafeDeleteModel
from django.core.validators import *
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField


class Peyk(models.Model):
    def __str__(self):
        return self.phone
    phone = models.CharField(max_length=15, unique=True, validators=[RegexValidator()])
    active = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    password = models.CharField(max_length=255, blank=True, null=True)
    vehicle = models.CharField(max_length=100, blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    activation_code = models.CharField(max_length=127, null=True, blank=True)
    activation_expire = models.DateTimeField(null=True, blank=True)
    access_token = models.TextField(max_length=255, null=True, blank=True)
    access_token_expire = models.DateTimeField(auto_now_add=True)


class Mission(models.Model):
    def __str__(self):
        return self.customer

    date = timezone.now().strftime("%Y-%m-%d")
    time = timezone.now().strftime("%H-%M-%S-%f")[:-4]
    name = models.CharField(max_length=255, default='گل ez53')
    image = models.FileField(upload_to='mehrpeyk/date/', null=True, blank=True, default='https://fyf.tac-cdn.net/images/products/large/BF116-11KM_R.jpg?auto=webp&quality=60')
    customer = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    factor_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=31, default=1)
    peyk = models.ForeignKey(Peyk, on_delete=models.PROTECT, null=True, blank=True)


@receiver(post_delete, sender=Mission)
def submission_delete(sender, instance, **kwargs):
    instance.file.delete(False)



class Location(models.Model):
    # def __str__(self):
    #     return self.points

    # points = models.MultiPointField()
    point = ArrayField(models.CharField(max_length=100, blank=True), size=2)
    created_at = models.DateTimeField(auto_now_add=True)
    mission = models.ForeignKey(Mission, on_delete=models.PROTECT)