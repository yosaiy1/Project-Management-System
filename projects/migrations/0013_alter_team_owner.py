# Generated by Django 5.1.4 on 2024-12-24 09:29

import django.db.models.deletion
import projects.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_alter_team_options_alter_team_owner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='owner',
            field=models.ForeignKey(default=projects.models.get_default_owner, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='owned_teams', to=settings.AUTH_USER_MODEL),
        ),
    ]
