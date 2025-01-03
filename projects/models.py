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
from django.db import models, transaction
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        error_messages={
            'unique': "A user with that email already exists.",
        },
        verbose_name='email address'
    )
    is_project_manager = models.BooleanField(
        default=True,  # Default is True for direct registration
        help_text='Designates whether this user can create team member accounts'
    )
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

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['username']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email'])
        ]

    def save(self, *args, **kwargs):
        """Override save to handle profile creation and team setup"""
        try:
            creating = not self.pk
            super().save(*args, **kwargs)
            
            if creating:
                # Create user profile
                Profile.objects.get_or_create(user=self)
                
                # Create default team for project managers
                if self.is_project_manager:
                    with transaction.atomic():
                        team = Team.objects.create(
                            name=f"{self.username}'s Team",
                            description=f"Default team for {self.username}",
                            owner=self
                        )
                        TeamMember.objects.create(
                            team=team,
                            user=self,
                            role='owner',
                            created_by=self
                        )
                        
                        # Notify user about team creation
                        self.notify(
                            f"Your default team '{team.name}' has been created",
                            notification_type='success',
                            action_type='team_created',
                            related_object=team
                        )
        except Exception as e:
            logger.error(f"Error in user save: {str(e)}")
            raise

    def notify(self, message, notification_type='info', action_type='other', related_object=None):
        """Create a notification for this user"""
        try:
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
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return None

    @property
    def is_admin(self):
        """Check if user has admin privileges"""
        return self.is_staff or self.is_superuser

    def is_manager(self):
        """Check if user is a project manager"""
        return (
            self.is_project_manager or 
            self.owned_teams.exists() or
            TeamMember.objects.filter(
                user=self,
                role__in=['owner', 'manager']
            ).exists()
        )

    def get_managed_teams(self):
        """Get teams where user is project manager"""
        return Team.objects.filter(
            Q(owner=self) |  # Teams owned by user
            Q(projects__manager=self) |  # Teams with projects managed by user
            Q(members__user=self, members__role__in=['owner', 'manager'])  # Teams where user is owner/manager
        ).distinct()

    def get_accessible_projects(self):
        """Get projects user has access to"""
        if self.is_project_manager:
            # Project managers see their owned/managed projects
            return Project.objects.filter(
                Q(team__owner=self) |  # Projects in owned teams
                Q(manager=self) |      # Directly managed projects
                Q(team__members__user=self)  # Projects in teams where user is member
            ).distinct()
        else:
            # Regular users only see projects they're assigned to
            return Project.objects.filter(
                Q(team__members__user=self) |  # Projects where user is team member
                Q(tasks__assigned_to=self)     # Projects with assigned tasks
            ).distinct()

    def get_accessible_teams(self):
        """Get teams user has access to"""
        if self.is_project_manager:
            # Project managers see their owned/managed teams
            return Team.objects.filter(
                Q(owner=self) |             # Teams they own
                Q(members__user=self) |     # Teams they're members of
                Q(projects__manager=self)   # Teams with projects they manage
            ).distinct()
        else:
            # Regular users only see teams they're members of
            return Team.objects.filter(members__user=self).distinct()

    def create_team_member(self, username, email, password, team):
        """Create a new team member account"""
        if not team.can_create_team_members(self):
            raise ValidationError("Only project managers or team owners can create team members")

        try:
            with transaction.atomic():
                # Check existing user
                if User.objects.filter(
                    Q(username__iexact=username) | 
                    Q(email__iexact=email)
                ).exists():
                    raise ValidationError("A user with that username or email already exists")
                
                # Create user
                user = User.objects.create_user(
                    username=username.lower(),
                    email=email.lower(),
                    password=password,
                    is_staff=False,
                    is_project_manager=False
                )
                
                # Create team membership
                member = TeamMember.objects.create(
                    team=team,
                    user=user,
                    role='member',
                    created_by=self
                )

                # Send notifications
                user.notify(
                    f"Account created by {self.username}. Welcome to {team.name}!",
                    notification_type='success',
                    action_type='team_joined',
                    related_object=team
                )

                if team.owner != self:
                    team.owner.notify(
                        f"New member {user.username} added to {team.name} by {self.username}",
                        notification_type='info',
                        action_type='team_member_added',
                        related_object=team
                    )

                return member

        except ValidationError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise ValidationError(f"Failed to create team member: {str(e)}")

    def get_all_notifications(self):
        """Get all notifications for user"""
        return self.notifications.all().order_by('-created_at')

    def get_unread_notifications(self):
        """Get unread notifications for user"""
        return self.notifications.filter(read=False).order_by('-created_at')

    def mark_notifications_read(self, notification_ids=None):
        """Mark notifications as read"""
        if notification_ids:
            self.notifications.filter(id__in=notification_ids).update(read=True)
        else:
            self.notifications.all().update(read=True)

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def __str__(self):
        return self.username

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


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
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='owned_teams',
        default=get_default_owner,
        null=True
    )
    avatar = models.ImageField(
        upload_to='team_avatars/',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'owner'],
                name='unique_team_name_per_owner'
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Validate team data"""
        if not self.name:
            raise ValidationError("Team name is required")
        if len(self.name) < 3:
            raise ValidationError("Team name must be at least 3 characters long")
        if not self.owner:
            raise ValidationError("Team must have an owner")

    def save(self, *args, **kwargs):
        self.clean()
        # Delete old avatar when updating
        if self.pk:
            try:
                old_team = Team.objects.get(pk=self.pk)
                if old_team.avatar and self.avatar != old_team.avatar:
                    old_team.avatar.delete(save=False)
            except Team.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def can_create_team_members(self, user):
        """Check if user can create team members"""
        if not user:
            return False
        return (
            user == self.owner or
            user.is_project_manager or
            TeamMember.objects.filter(
                team=self,
                user=user,
                role__in=['owner', 'manager']
            ).exists()
        )

    def can_manage_team(self, user):
        """Check if user can manage team"""
        if not user:
            return False
        return (
            user == self.owner or
            user.is_project_manager or
            TeamMember.objects.filter(
                team=self,
                user=user,
                role__in=['owner', 'manager']
            ).exists()
        )

    def add_member(self, user, role='member', created_by=None):
        """Add a new team member"""
        if not user:
            raise ValidationError("User is required")
        
        try:
            # Check if user is already a member
            if TeamMember.objects.filter(team=self, user=user).exists():
                raise ValidationError("User is already a member of this team")

            # Validate role
            if role not in dict(TeamMember.ROLE_CHOICES):
                raise ValidationError("Invalid role specified")

            member = TeamMember.objects.create(
                team=self,
                user=user,
                role=role,
                created_by=created_by
            )

            # Send notifications
            user.notify(
                f"You have been added to team: {self.name}",
                notification_type='success',
                action_type='team_joined',
                related_object=self
            )

            if created_by and created_by != self.owner:
                self.owner.notify(
                    f"{user.username} was added to {self.name} by {created_by.username}",
                    notification_type='info',
                    action_type='team_member_added',
                    related_object=self
                )

            return member
        except Exception as e:
            logger.error(f"Error adding team member: {str(e)}")
            raise ValidationError(f"Failed to add team member: {str(e)}")

    def remove_member(self, user, notify=True, reason=None):
        """Remove a team member"""
        if not user:
            raise ValidationError("User is required")
            
        try:
            if user == self.owner:
                raise ValidationError("Cannot remove team owner")

            member = TeamMember.objects.get(team=self, user=user)

            # Reassign or update tasks
            Task.objects.filter(
                assigned_to=user,
                project__team=self
            ).update(
                assigned_to=None,
                status='unassigned',
                updated_at=timezone.now()
            )

            member.delete()

            # Send notification
            user.notify(
                f"You have been removed from team: {self.name}",
                notification_type='warning',
                action_type='team_left',
                related_object=self
            )

            # Send email notification
            if notify:
                from .utils.email import send_team_removal_email
                sent = send_team_removal_email(user, self, reason)
                if not sent:
                    logger.warning(f"Failed to send removal email to {user.email}")

            return True

        except TeamMember.DoesNotExist:
            raise ValidationError("User is not a member of this team")
        except Exception as e:
            logger.error(f"Error removing team member: {str(e)}")
            raise ValidationError(f"Failed to remove team member: {str(e)}")

    @property
    def active_members(self):
        """Get count of active team members"""
        return self.members.count()

    def calculate_progress(self):
        """Calculate overall team progress"""
        try:
            tasks = Task.objects.filter(project__team=self)
            total = tasks.count()
            if total == 0:
                return 0
            completed = tasks.filter(status='done').count()
            return round((completed / total) * 100, 1)
        except Exception as e:
            logger.error(f"Error calculating team progress: {str(e)}")
            return 0

    def get_managers(self):
        """Get all team managers"""
        return self.members.filter(
            role__in=['owner', 'manager']
        ).select_related('user')

    def get_member_stats(self):
        """Get statistics for all team members"""
        try:
            return self.members.annotate(
                task_count=Count('user__assigned_tasks'),
                completed_tasks=Count(
                    'user__assigned_tasks',
                    filter=Q(user__assigned_tasks__status='done')
                ),
                completion_rate=Case(
                    When(task_count=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('completed_tasks') * 100.0 / F('task_count'),
                        output_field=FloatField()
                    ),
                    output_field=FloatField()
                )
            ).select_related('user')
        except Exception as e:
            logger.error(f"Error getting member stats: {str(e)}")
            return self.members.none()

class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),      # Full control over team
        ('manager', 'Manager'),  # Can manage projects and members
        ('member', 'Member')     # Basic access and assigned tasks
    ]

    team = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    date_joined = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        related_name='created_members',
        null=True,
        blank=True  
    )

    def has_team_access(self):
        """Check if member has basic team access"""
        # Project managers can access teams they create
        if self.user.is_project_manager:
            return True
        # Regular members need explicit team membership
        return self.team.members.filter(user=self.user).exists()

    def has_project_permission(self, project):
        """Check if member has permission to access/modify project"""
        try:
            # Project managers have full access to their projects
            if self.user.is_project_manager and (
                project.manager == self.user or 
                project.team.owner == self.user
            ):
                return True

            # Team owners have full access
            if self.role == 'owner':
                return True

            # Managers can access projects they manage or are assigned to
            if self.role == 'manager':
                return (
                    self.team == project.team and 
                    (self.user == project.manager or 
                     project.tasks.filter(assigned_to=self.user).exists())
                )

            # Members can only access projects they're assigned to
            return (
                project.team == self.team and
                project.tasks.filter(assigned_to=self.user).exists()
            )
        except Exception:
            return False

    def can_manage_members(self):
        """Check if member can manage other team members"""
        return self.role in ['owner', 'manager']

    def can_assign_tasks(self):
        """Check if member can assign tasks to others"""
        return self.role in ['owner', 'manager']

    def can_create_projects(self):
        """Check if member can create new projects"""
        return self.role in ['owner', 'manager']

    def get_assigned_tasks(self):
        """Get all tasks assigned to this member"""
        try:
            return Task.objects.filter(
                assigned_to=self.user,
                project__team=self.team
            ).select_related('project')
        except Exception:
            return Task.objects.none()

    def get_projects(self):
        """Get all accessible projects for this member"""
        try:
            # Owners can see all team projects
            if self.role == 'owner':
                return self.team.projects.all()

            # Managers can see projects they manage or are assigned to
            if self.role == 'manager':
                return Project.objects.filter(
                    team=self.team
                ).filter(
                    Q(manager=self.user) | Q(tasks__assigned_to=self.user)
                ).distinct()

            # Members can only see projects with assigned tasks
            return Project.objects.filter(
                team=self.team,
                tasks__assigned_to=self.user
            ).distinct()
        except Exception:
            return Project.objects.none()

    def clean(self):
        """Validate role assignments"""
        try:
            # Handle new member creation
            if not self.pk:
                if self.user == self.team.owner:
                    self.role = 'owner'
                elif self.role == 'owner' and self.user != self.team.owner:
                    raise ValidationError("Only the team owner can have the owner role")
            # Handle existing member updates
            else:
                if self.role == 'owner' and self.user != self.team.owner:
                    raise ValidationError("Only the team owner can have the owner role")
                if self.user == self.team.owner and self.role != 'owner':
                    raise ValidationError("Team owner must maintain owner role")
        except Exception as e:
            raise ValidationError(f"Validation error: {str(e)}")

    def save(self, *args, **kwargs):
        """Handle role assignment and notifications"""
        try:
            is_new = not self.pk
            
            # Set initial roles
            if is_new:
                if self.user == self.team.owner:
                    self.role = 'owner'
                elif self.user.is_project_manager:
                    self.role = 'manager'

            self.full_clean()
            super().save(*args, **kwargs)

            # Send notifications for new members
            if is_new and hasattr(self.user, 'notify'):
                self.user.notify(
                    f"You have been added to team: {self.team.name}",
                    notification_type='success',
                    action_type='team_joined',
                    related_object=self.team
                )

                if self.team.owner != self.user:
                    self.team.owner.notify(
                        f"{self.user.username} has joined the team: {self.team.name}",
                        notification_type='info',
                        action_type='team_member_added',
                        related_object=self.team
                    )
        except Exception as e:
            raise ValidationError(f"Error saving team member: {str(e)}")

    def get_completion_rate(self):
        """Calculate task completion rate"""
        try:
            tasks = self.get_assigned_tasks()
            total = tasks.count()
            if not total:
                return 0
            completed = tasks.filter(status='done').count()
            return round((completed / total) * 100, 1)
        except Exception:
            return 0

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

    def get_member_role(self, user):
        """Get member's role in the project team"""
        try:
            member = TeamMember.objects.get(team=self.team, user=user)
            return member.role
        except TeamMember.DoesNotExist:
            return None
    
    def is_assigned_to(self, user):
        """Check if user has tasks assigned in this project"""
        return self.tasks.filter(assigned_to=user).exists()

    def get_user_role(self, user):
        """Get user's role in the project"""
        member_role = self.get_member_role(user)
        if member_role:
            return member_role
        elif user == self.manager:
            return 'manager'
        elif self.is_assigned_to(user):
            return 'assigned'
        return None

    def can_create_team_members(self, user):
        """Check if user can create team members for this project"""
        member_role = self.get_member_role(user)
        return (
            user == self.manager or 
            member_role in ['owner', 'manager'] or
            user.is_project_manager
        )

    def create_team_member(self, username, email, password, created_by):
        """Create a new team member for this project"""
        if not self.can_create_team_members(created_by):
            raise ValidationError("Only project managers or team owners can create team members")
            
        try:
            with transaction.atomic():
                # Check if user already exists
                user = User.objects.filter(Q(username=username) | Q(email=email)).first()
                if user:
                    raise ValidationError("User with this username or email already exists")
                
                # Create new user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_staff=False,
                    is_project_manager=False
                )
                
                # Create team membership
                member = TeamMember.objects.create(
                    team=self.team,
                    user=user,
                    role='member',
                    created_by=created_by
                )
                
                # Create profile
                Profile.objects.create(user=user)
                
                # Send notifications
                user.notify(
                    f"Account created by {created_by.username}. Added to project {self.name}",
                    notification_type='success',
                    action_type='team_joined',
                    related_object=self
                )
                
                self.team.owner.notify(
                    f"New member {user.username} added to project {self.name} by {created_by.username}",
                    notification_type='info',
                    action_type='team_member_added',
                    related_object=self
                )
                
                return member
        except Exception as e:
            raise ValidationError(f"Failed to create team member: {str(e)}")

    def get_team_members(self):
        """Get all team members for this project"""
        return TeamMember.objects.filter(
            team=self.team
        ).select_related('user', 'user__profile')

    def get_managers(self):
        """Get all managers for this project"""
        return TeamMember.objects.filter(
            team=self.team,
            role__in=['owner', 'manager']
        ).select_related('user')

    @property
    def files(self):
        """Get all files associated with this project's tasks"""
        return File.objects.filter(
            task__project=self
        ).select_related('task', 'uploaded_by')

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

    project = models.ForeignKey(
        'Project', 
        on_delete=models.CASCADE, 
        related_name='tasks'
    )
    title = models.CharField(
        max_length=200,
        help_text="Enter a clear, descriptive title for the task"
    )
    description = models.TextField(
        blank=True,
        help_text="Provide detailed information about the task"
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assigned_tasks'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    start_date = models.DateField()
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'title'],
                name='unique_task_title_in_project'
            )
        ]

    def clean(self):
        """Validate task data"""
        if not self.title:
            raise ValidationError("Task title is required")
            
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError("Due date must be after start date")
            
        if self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
            
        # Validate assigned user has access to project
        if self.assigned_to and self.project:
            from .utils.permissions import has_project_permission
            if not has_project_permission(self.assigned_to, self.project):
                raise ValidationError("Assigned user does not have access to this project")

    tracker = FieldTracker(fields=['status'])

    def save(self, *args, **kwargs):
        """Save task with proper validation and status handling"""
        self.clean()
        if self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'done':
            self.completed_at = None
        self.last_active = timezone.now()
        super().save(*args, **kwargs)

    def get_progress(self):
        """Calculate task progress based on status"""
        if self.status == 'done':
            return 100
        elif self.status == 'inprogress':
            return 50
        return 0

    def is_overdue(self):
        """Check if task is overdue"""
        if self.status == 'done':
            return False
        return self.due_date < timezone.now().date()

    def __str__(self):
        return self.title

class File(models.Model):
    task = models.ForeignKey(
        Task, 
        on_delete=models.CASCADE, 
        related_name='files'
    )
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='uploaded_files'
    )
    file_name = models.CharField(
        max_length=200,
        help_text="Name of the uploaded file"
    )
    file = models.FileField(
        upload_to='files/',
        help_text="Upload task-related files (max 10MB)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['task', 'file_name'],
                name='unique_file_name_in_task'
            )
        ]

    def clean(self):
        """Validate file data"""
        if not self.file_name and self.file:
            self.file_name = self.file.name
            
        if self.file.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationError("File size cannot exceed 10MB")

    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted"""
        self.file.delete(save=False)
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