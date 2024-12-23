# Generated by Django 5.1.4 on 2024-12-24 09:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_alter_team_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='team',
            options={'verbose_name': 'Team', 'verbose_name_plural': 'Teams'},
        ),
        migrations.AlterUniqueTogether(
            name='file',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='notification',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='task',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='teammember',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='team',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_teams', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='file',
            constraint=models.UniqueConstraint(fields=('task', 'file_name'), name='unique_file_name_in_task'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=('name', 'team'), name='unique_project_name_in_team'),
        ),
        migrations.AddConstraint(
            model_name='task',
            constraint=models.UniqueConstraint(fields=('project', 'title'), name='unique_task_title_in_project'),
        ),
        migrations.AddConstraint(
            model_name='teammember',
            constraint=models.UniqueConstraint(fields=('team', 'user'), name='unique_team_member'),
        ),
    ]
