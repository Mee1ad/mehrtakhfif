# Generated by Django 2.2.3 on 2019-10-06 17:42

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0011_auto_20191006_1715'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='location',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=100), blank=True, null=True, size=2),
        ),
    ]