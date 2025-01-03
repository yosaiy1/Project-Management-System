from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Homepage & Dashboard URLs
    path('', views.homepage, name='homepage'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/overview/', views.dashboard_overview, name='dashboard_overview'),
    
    # Project URLs
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/update/', views.project_update, name='project_update'),
    path('projects/<int:project_id>/delete/', views.project_delete, name='project_delete'),
    path('projects/<int:project_id>/stats/', views.project_stats, name='project_stats'),
    path('projects/<int:project_id>/timeline/', views.project_timeline, name='project_timeline'),
    path('teams/projects/<int:project_id>/team-members/', views.get_project_team_members, name='project_team_members'),
    
    # Task URLs
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/quick-create/', views.quick_create_task, name='quick_create_task'),
    path('tasks/status/<int:task_id>/', views.update_task_status, name='update_task_status'),
    path('projects/<int:project_id>/tasks/create/', views.task_create, name='project_task_create'),
    path('projects/<int:project_id>/tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('projects/<int:project_id>/tasks/<int:task_id>/update/', views.task_update, name='task_update'),
    path('projects/<int:project_id>/tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),
    
    # Team URLs
    path('teams/', views.team_list, name='team_list'),
    path('teams/create/', views.team_form, name='team_create'),
    path('teams/<int:team_id>/edit/', views.team_form, name='team_edit'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    path('teams/<int:team_id>/projects/', views.team_projects, name='team_projects'),
    path('teams/members/', views.all_team_members, name='all_team_members'),
    
    # Team Member Management URLs
    path('teams/<int:team_id>/members/', views.manage_team_members, name='manage_team_members'),
    path('teams/<int:team_id>/invite/', views.invite_team_member, name='team_invite_member'),
    path('teams/<int:team_id>/members/add/', views.add_team_member, name='add_team_member'),
    path('teams/<int:team_id>/members/<int:member_id>/edit-role/', views.update_member_role, name='update_member_role'),
    path('teams/<int:team_id>/members/<int:member_id>/remove/', views.remove_team_member, name='remove_team_member'),
    path('teams/<int:team_id>/members/<int:member_id>/', views.member_detail, name='member_detail'),
    path('teams/<int:team_id>/members/<int:member_id>/tasks/', views.member_tasks, name='member_tasks'),
    path('teams/<int:team_id>/create-member/', views.create_team_member, name='create_team_member'),
    
    # Notification URLs
    path('notifications/', views.notification_list, name='notifications'),
    path('notifications/clear/', views.clear_all_notifications, name='clear_notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    
    # User & Profile URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('profile/update-avatar/', views.update_avatar, name='update_avatar'),
    
    # Password Reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Search & API URLs
    path('search/', views.search_view, name='search'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/tasks/<int:task_id>/update-status/', views.update_task_status, name='update_task_status'),
    path('api/analytics/data/', views.analytics_data, name='analytics_data'),
    
    # Analytics & Reports URLs
    path('progress/', views.progress, name='progress'),
    path('progress/members/', views.member_progress, name='member_progress'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('reports/', views.reports_view, name='reports'),
    
    # Settings URLs
    path('settings/', views.settings_view, name='settings'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('profile/remove-avatar/', views.remove_avatar, name='remove_avatar'),
    
    # File Management URLs
    path('projects/<int:project_id>/files/', views.project_files, name='project_files'),
    path('projects/<int:project_id>/files/upload/', views.upload_file, name='upload_file'),
    path('files/<int:file_id>/delete/', views.delete_file, name='delete_file'),
]

# Error Handlers
handler404 = 'projects.views.handler404'
handler500 = 'projects.views.handler500'
handler403 = 'projects.views.handler403'