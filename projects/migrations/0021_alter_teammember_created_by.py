# Generated by Django 5.1.4 on 2025-01-03 01:17

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0020_alter_teammember_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teammember',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_members', to=settings.AUTH_USER_MODEL),
        ),
    ]