from django.contrib import admin
from django.contrib import messages
from django import forms
from django.forms.models import BaseInlineFormSet
from .models import User, Team, TeamMember, Project, Task, File, Notification, ProjectReport, Profile

# Inline for Profile Model
class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 1  # Number of empty forms to display by default


# Inline formset for TeamMember to enforce uniqueness
class UniqueTeamMemberInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_users = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            user = form.cleaned_data.get('user')
            if user in seen_users:
                raise forms.ValidationError("Each user can only be added to the team once.")
            seen_users.add(user)


# Inline admin for TeamMember
class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    formset = UniqueTeamMemberInlineFormSet
    extra = 1  # Number of empty forms to display by default
    fields = ['user', 'team']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email')
    search_fields = ['username', 'email']
    inlines = [ProfileInline]  # Add Profile inline for each user

    def delete_model(self, request, obj):
        # Prevent deletion of a user if they are assigned to a task or team member
        if obj.task_set.exists() or obj.teammember_set.exists():
            self.message_user(
                request,
                f"Cannot delete user '{obj.username}' because they are associated with tasks or teams.",
                messages.ERROR
            )
            return
        super().delete_model(request, obj)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    inlines = [TeamMemberInline]  # Allow team members to be added inline
    search_fields = ['name', 'description']  # Enable search functionality

    def delete_model(self, request, obj):
        # Prevent deletion of a team if it has associated team members or projects
        if obj.teammember_set.exists() or obj.project_set.exists():
            self.message_user(
                request,
                f"Cannot delete team '{obj.name}' because it has members or projects.",
                messages.ERROR
            )
            return
        super().delete_model(request, obj)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'team')
    raw_id_fields = ('user',)  # Use raw ID fields for User


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'start_date', 'end_date')
    search_fields = ['name']
    list_filter = ['team']
    raw_id_fields = ('team',)  # Use raw ID fields for Team
    autocomplete_fields = ['team']  # Enable autocomplete for smoother team selection


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
    readonly_fields = ('date_sent',)

    @admin.action(description='Mark selected as read')
    def mark_as_read(self, request, queryset):
        queryset.update(read=True)

    @admin.action(description='Mark selected as unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(read=False)

    actions = [mark_as_read, mark_as_unread]


@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'generated_on')
    search_fields = ['project__name']  # Enable search by project name


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'profile_picture')
