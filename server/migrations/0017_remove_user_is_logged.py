# Generated by Django 2.2.3 on 2019-10-09 23:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0016_auto_20191008_1710'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_logged',
        ),
    ]