from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)  # Enforce unique emails
    
    # Define if the user is an admin using the built-in `is_staff` field or a custom field
    is_admin = models.BooleanField(default=False)  # Optional: you could also use is_staff or is_superuser

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

    def is_admin(self):
        return self.is_staff  # Alternatively, you could use `is_admin` as a custom admin flag

# Profile Model
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)  # User bio
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)  # Profile picture
    date_of_birth = models.DateField(null=True, blank=True)  # Date of birth
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # User's phone number

    def __str__(self):
        return f"Profile of {self.user.username}"

def get_default_owner():
    return User.objects.first()  # This will return the first User or None if no users exist

class Team(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_teams', 
        default=get_default_owner,  # Using the default function to set the owner
        null=True,  # Allowing null temporarily
    )

    def __str__(self):
        return self.name

# TeamMember Model
class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teams')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['team', 'user'], name='unique_team_member')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.team.name}"

# Project Model
class Project(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'team'], name='unique_project_name_in_team')
        ]

    def __str__(self):
        return self.name

# Task Model
class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    due_date = models.DateField()
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('inprogress', 'In Progress'),
        ('done', 'Done'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project', 'title'], name='unique_task_title_in_project')
        ]

    def __str__(self):
        return self.title

# File Model
class File(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    file_name = models.CharField(max_length=200)
    file = models.FileField(upload_to='files/')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['task', 'file_name'], name='unique_file_name_in_task')
        ]

    def __str__(self):
        return self.file_name

# Notification Model
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}"

# ProjectReport Model
class ProjectReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    generated_on = models.DateTimeField(auto_now_add=True)
    content = models.TextField()

    def __str__(self):
        return f"Report for {self.project.name}"
