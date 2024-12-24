# Generated by Django 5.1.4 on 2024-12-16 14:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_remove_user_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bio', models.TextField(blank=True, null=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profiles/%Y/%m/%d/')),  # Structured path for uploads
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),  # Optionally set unique=True if needed
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
