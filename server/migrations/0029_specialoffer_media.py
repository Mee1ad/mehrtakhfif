# Generated by Django 2.2.3 on 2019-09-01 09:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0028_auto_20190901_0146'),
    ]

    operations = [
        migrations.AddField(
            model_name='specialoffer',
            name='media',
            field=models.ForeignKey(default=42, on_delete=django.db.models.deletion.CASCADE, to='server.Media'),
            preserve_default=False,
        ),
    ]
