# Generated by Django 2.2.3 on 2019-09-01 13:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0032_auto_20190901_1147'),
    ]

    operations = [
        migrations.RenameField(
            model_name='menu',
            old_name='link',
            new_name='url',
        ),
    ]
