# Generated by Django 5.1.4 on 2024-12-29 16:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0008_alter_teammember_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='last_active',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='task',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
