# Generated by Django 2.2.3 on 2019-10-08 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0014_user_full_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_logged',
            field=models.BooleanField(default=False, verbose_name='Logged in'),
        ),
    ]