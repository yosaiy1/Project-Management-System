from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)  # Enforce unique emails

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.username


# Profile Model
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)  # User bio
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)  # Profile picture
    date_of_birth = models.DateField(null=True, blank=True)  # Date of birth
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # User's phone number

    def __str__(self):
        return f"Profile of {self.user.username}"


# Team Model
class Team(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.name


# TeamMember Model
class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('team', 'user')  # Prevent duplicates

    def __str__(self):
        return f"{self.user.username} - {self.team.name}"


# Project Model
class Project(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


# Task Model
class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    due_date = models.DateField()

    class Meta:
        unique_together = ('project', 'title')  # Prevent duplicate task titles within the same project

    def __str__(self):
        return self.title


# Files Model
class File(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=200)

    class Meta:
        unique_together = ('task', 'file_name')  # Prevent duplicate file names for the same task

    def __str__(self):
        return self.file_name


# Notification Model
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'message')  # Prevent duplicate notifications

    def __str__(self):
        return f"Notification for {self.user.username}"


# ProjectReport Model
class ProjectReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    generated_on = models.DateTimeField(auto_now_add=True)
    content = models.TextField()

    def __str__(self):
        return f"Report for {self.project.name}"
