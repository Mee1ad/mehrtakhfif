# Generated by Django 2.2.3 on 2019-08-25 15:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0022_specialproducts_box'),
    ]

    operations = [
        migrations.AddField(
            model_name='storage',
            name='category',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='server.Category'),
            preserve_default=False,
        ),
    ]
