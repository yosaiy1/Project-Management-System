# Generated by Django 5.1.4 on 2024-12-29 06:44

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='project',
            options={'ordering': ['-created_at']},
        ),
        migrations.RemoveConstraint(
            model_name='task',
            name='unique_task_title_in_project',
        ),
        migrations.RenameField(
            model_name='project',
            old_name='date_created',
            new_name='created_at',
        ),
        migrations.RemoveField(
            model_name='project',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='task',
            name='updated_at',
        ),
        migrations.AddField(
            model_name='project',
            name='manager',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='managed_projects', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='project',
            name='status',
            field=models.CharField(choices=[('planned', 'Planned'), ('active', 'Active'), ('completed', 'Completed'), ('on_hold', 'On Hold')], default='planned', max_length=20),
        ),
        migrations.AddField(
            model_name='task',
            name='priority',
            field=models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium', max_length=20),
        ),
        migrations.AlterField(
            model_name='task',
            name='assigned_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_tasks', to=settings.AUTH_USER_MODEL),
        ),
    ]
