# Generated by Django 2.2.3 on 2019-09-29 13:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mehrpeyk', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mission',
            name='peyk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='mehrpeyk.Peyk'),
        ),
        migrations.AddField(
            model_name='peyk',
            name='access_token',
            field=models.TextField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='peyk',
            name='access_token_expire',
            field=models.DateTimeField(auto_now_add=True, default='2019-09-22 13:25:22.9404+03:30'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='peyk',
            name='activation_code',
            field=models.CharField(blank=True, max_length=127, null=True),
        ),
        migrations.AddField(
            model_name='peyk',
            name='activation_expire',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='peyk',
            name='moaref',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='peyk',
            name='verified',
            field=models.BooleanField(default=False),
        ),
    ]
