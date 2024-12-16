from django.contrib import admin
from .models import User, Team, TeamMember, Project, Task, File, Notification, ProjectReport, Profile

# Inline for Profile Model
class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 1  # Number of empty forms to display by default

# Inline admin for TeamMember to be added directly from Team admin
class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 1  # Number of empty forms to display by default
    fields = ['user', 'team']  # Make sure that user and team fields are included

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email')  # Removed 'role' field
    inlines = [ProfileInline]  # Add Profile inline for each user

    def delete_model(self, request, obj):
        # Prevent deletion of a user if they are assigned to a task or team member
        if obj.task_set.exists() or obj.teammember_set.exists():
            raise Exception(f"Cannot delete user '{obj.username}' because they are associated with tasks or teams.")
        super().delete_model(request, obj)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    inlines = [TeamMemberInline]  # Allow team members to be added inline
    search_fields = ['name', 'description']  # Enable search functionality for autocomplete

    def delete_model(self, request, obj):
        # Prevent deletion of a team if it has associated team members or projects
        if obj.teammember_set.exists() or obj.project_set.exists():
            raise Exception(f"Cannot delete team '{obj.name}' because it has members or projects.")
        super().delete_model(request, obj)

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'team')
    raw_id_fields = ('user',)  # Use raw ID fields for User (useful for large user lists)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'start_date', 'end_date')
    search_fields = ['name']
    list_filter = ['team']
    raw_id_fields = ('team',)  # Use raw ID fields for Team (useful for large team lists)
    autocomplete_fields = ['team']  # Use autocomplete for smoother team selection

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'start_date', 'due_date')
    search_fields = ['title']
    list_filter = ['project', 'assigned_to']

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'task', 'uploaded_by')
    search_fields = ['file_name']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'date_sent', 'read')
    list_filter = ['user', 'read']

@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'generated_on')
    search_fields = ['project__name']  # Enable search by project name

# Optional separate profile admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'profile_picture')
