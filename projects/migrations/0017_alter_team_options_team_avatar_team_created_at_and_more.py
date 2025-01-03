# Generated by Django 5.1.4 on 2024-12-31 18:34

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0016_alter_teammember_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='team',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='team',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='team_avatars/'),
        ),
        migrations.AddField(
            model_name='team',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='team',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='team',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='team',
            name='name',
            field=models.CharField(max_length=200, unique=True),
        ),
        migrations.AddConstraint(
            model_name='team',
            constraint=models.UniqueConstraint(fields=('name', 'owner'), name='unique_team_name_per_owner'),
        ),
    ]
