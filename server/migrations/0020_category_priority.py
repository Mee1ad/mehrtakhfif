# Generated by Django 2.2.3 on 2019-08-25 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0019_storage_box'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='priority',
            field=models.SmallIntegerField(default=0),
        ),
    ]
