from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.db.models import signals
from model_utils.tracker import FieldTracker
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    email = models.EmailField(unique=True)
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

    def notify(self, message, notification_type='info', action_type='other', related_object=None):
        """Create a notification for this user"""
        notification = self.notifications.create(
            message=message,
            notification_type=notification_type,
            action_type=action_type,
            read=False
        )
        if related_object:
            notification.content_type = ContentType.objects.get_for_model(related_object)
            notification.object_id = related_object.id
            notification.save()
        return notification

    @property
    def is_admin(self):
        return self.is_staff

    def __str__(self):
        return self.username

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    def clean(self):
        if self.date_of_birth and self.date_of_birth > timezone.now().date():
            raise ValidationError("Date of birth cannot be in the future")

def get_default_owner():
    return User.objects.first()

class Team(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_teams',
        default=get_default_owner,
        null=True,
    )

    def clean(self):
        if not self.owner:
            raise ValidationError("Team must have an owner")

    def __str__(self):
        return self.name

class TeamMember(models.Model):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    )
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['team', 'user'], name='unique_team_member')
        ]

    @property
    def projects(self):
        """Get all projects associated with this team member"""
        return self.team.projects.filter(team=self.team)

    @property
    def project_count(self):
        """Get count of projects user is involved in within this team"""
        return self.projects.count()

    @property
    def tasks(self):
        """Get all tasks assigned to this team member"""
        return Task.objects.filter(project__team=self.team, assigned_to=self.user)

    @property
    def task_count(self):
        """Get count of tasks assigned to user within this team"""
        return self.tasks.count()

    @property
    def completed_tasks_count(self):
        """Get count of completed tasks by user within this team"""
        return self.tasks.filter(status='done').count()

    @property
    def project_completion_rate(self):
        """Calculate project completion rate for this member"""
        total = self.project_count
        if not total:
            return 0
        completed = self.projects.filter(status='completed').count()
        return int((completed / total) * 100)

class Project(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold')
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='projects')
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_projects')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['name', 'team'], name='unique_project_name_in_team')
        ]

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date must be after start date")
        
        if self.status == 'completed' and not self.end_date:
            raise ValidationError("Completed projects must have an end date")

    def __str__(self):
        return self.name

class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('inprogress', 'In Progress'),
        ('done', 'Done')
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    start_date = models.DateField()
    due_date = models.DateField()
    tracker = FieldTracker(fields=['status'])
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Add this field
    last_active = models.DateTimeField(auto_now=True)  # Add this field

    def clean(self):
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError("Due date must be after start date")

    def save(self, *args, **kwargs):
        if self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'done':
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class File(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    file_name = models.CharField(max_length=200)
    file = models.FileField(upload_to='files/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['task', 'file_name'], name='unique_file_name_in_task')
        ]

    def clean(self):
        if not self.file_name:
            self.file_name = self.file.name

    def delete(self, *args, **kwargs):
        self.file.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.file_name

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error')
    ]
    
    ACTION_TYPES = [
        ('task_assigned', 'Task Assigned'),
        ('task_status_changed', 'Task Status Changed'),
        ('task_completed', 'Task Completed'),
        ('project_created', 'Project Created'),
        ('project_updated', 'Project Updated'),
        ('project_completed', 'Project Completed'),
        ('team_joined', 'Team Joined'),
        ('team_left', 'Team Left'),
        ('deadline_approaching', 'Deadline Approaching'),
        ('mention', 'Mention'),
        ('other', 'Other')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES, default='other')
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'read']),
            models.Index(fields=['action_type']),
        ]
        
    def __str__(self):
        return f"{self.get_action_type_display()} for {self.user.username}"

# Update task notification signal
@receiver(post_save, sender=Task)
def task_notification(sender, instance, created, **kwargs):
    """Send notifications for task events"""
    try:
        if created:
            instance.assigned_to.notify(
                f"You have been assigned to task: {instance.title}",
                notification_type='info',
                action_type='task_assigned',
                related_object=instance
            )
        else:
            old_status = instance.tracker.previous('status')
            if old_status and old_status != instance.status:
                instance.assigned_to.notify(
                    f"Task '{instance.title}' status changed to {instance.get_status_display()}",
                    notification_type='info',
                    action_type='task_status_changed',
                    related_object=instance
                )
            
            if instance.status == 'done':
                instance.project.manager.notify(
                    f"Task '{instance.title}' has been completed",
                    notification_type='success',
                    action_type='task_completed',
                    related_object=instance
                )
    except Exception as e:
        print(f"Error sending task notification: {e}")

# Add task deadline notification
@receiver(signals.pre_save, sender=Task)
def check_task_deadline(sender, instance, **kwargs):
    """Send notification when task is approaching deadline"""
    if not instance.pk:  # Skip for new tasks
        return
        
    try:
        today = timezone.now().date()
        days_until_due = (instance.due_date - today).days
        
        if days_until_due <= 2 and days_until_due >= 0:
            instance.assigned_to.notify(
                f"Task '{instance.title}' is due in {days_until_due} days",
                notification_type='warning',
                action_type='deadline_approaching',
                related_object=instance
            )
    except Exception as e:
        print(f"Error checking task deadline: {e}")

@receiver(post_save, sender=Project)
def project_notification(sender, instance, created, **kwargs):
    """Send notifications for project events"""
    if created:
        for member in instance.team.members.all():
            member.user.notify(
                f"New project created: {instance.name}",
                notification_type='info',
                action_type='project_created',
                related_object=instance
            )
    elif instance.status == 'completed':
        for member in instance.team.members.all():
            member.user.notify(
                f"Project '{instance.name}' has been completed",
                notification_type='success',
                action_type='project_completed',
                related_object=instance
            )

@receiver(post_save, sender=TeamMember)
def team_member_notification(sender, instance, created, **kwargs):
    """Send notifications for team member events"""
    try:
        if created:
            # Notify new member
            instance.user.notify(
                f"You have been added to team: {instance.team.name}",
                notification_type='success',
                action_type='team_joined',
                related_object=instance.team
            )
            # Notify team owner
            instance.team.owner.notify(
                f"{instance.user.username} has joined the team: {instance.team.name}",
                notification_type='info',
                action_type='team_joined',
                related_object=instance.team
            )
    except Exception as e:
        print(f"Error sending team member notification: {e}")

class ProjectReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    generated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,  # Allow null if user is deleted
        related_name='generated_reports',
        null=True,  # Make field optional
        blank=True
    )
    generated_on = models.DateTimeField(auto_now_add=True)
    content = models.TextField(blank=True)
    report_type = models.CharField(max_length=50, default='general')
    
    class Meta:
        ordering = ['-generated_on']
        
    def __str__(self):
        return f"Report for {self.project.name}"
    
    def generate_report(self):
        """Generate project report content"""
        tasks = self.project.tasks.all()
        completed = tasks.filter(status='done').count()
        total = tasks.count()
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        self.content = f"""
        Project: {self.project.name}
        Status: {self.project.get_status_display()}
        Tasks Completed: {completed}/{total} ({completion_rate:.1f}%)
        """
        self.save()

# Signals
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile for every new User"""
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save Profile whenever User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()