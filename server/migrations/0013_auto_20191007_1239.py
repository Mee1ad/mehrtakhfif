# Generated by Django 2.2.3 on 2019-10-07 12:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0012_auto_20191006_1742'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comment',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='updated_by',
        ),
    ]
