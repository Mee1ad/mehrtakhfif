# Generated by Django 2.2.3 on 2019-08-19 10:53

from django.db import migrations, models
import server.models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0012_auto_20190818_1738'),
    ]

    operations = [
        migrations.AddField(
            model_name='media',
            name='image',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='media',
            name='file',
            field=models.FileField(upload_to=server.models.upload_to),
        ),
    ]
