# Generated by Django 5.1.4 on 2025-01-01 14:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0018_alter_file_options_alter_task_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='is_project_manager',
            field=models.BooleanField(default=True, help_text='Designates whether this user can create team member accounts'),
        ),
    ]
