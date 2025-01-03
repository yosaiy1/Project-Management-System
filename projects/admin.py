from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib import messages
from django import forms
from django.forms.models import BaseInlineFormSet
from .models import User, Team, TeamMember, Project, Task, File, Notification, ProjectReport, Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profiles'

class CustomUserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'is_staff', 'is_superuser')
    search_fields = ['username', 'email']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email',)}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    def delete_model(self, request, obj):
        if obj.assigned_tasks.exists() or obj.team_memberships.exists():
            self.message_user(
                request,
                f"Cannot delete user '{obj.username}' because they are associated with tasks or teams.",
                messages.ERROR
            )
            return
        super().delete_model(request, obj)

admin.site.register(User, CustomUserAdmin)

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

class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    formset = UniqueTeamMemberInlineFormSet
    extra = 1
    fields = ['user', 'team']

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    inlines = [TeamMemberInline]
    search_fields = ['name', 'description']

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('team', 'user')
    search_fields = ['team__name', 'user__username']

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'start_date', 'end_date')
    search_fields = ['name', 'team__name']
    list_filter = ('team', 'start_date', 'end_date')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'start_date', 'due_date', 'status')
    search_fields = ['title', 'project__name', 'assigned_to__username']
    list_filter = ('status', 'project', 'assigned_to')

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'task', 'uploaded_by', 'created_at')
    search_fields = ['file_name', 'task__title', 'uploaded_by__username']
    list_filter = ('task', 'uploaded_by')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at', 'read')  # Changed from date_sent
    list_filter = ('read', 'created_at')  # Changed from date_sent
    search_fields = ['user__username', 'message']
    ordering = ('-created_at',)  # Changed from date_sent

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
    search_fields = ['project__name']
    list_filter = ('project', 'generated_on')