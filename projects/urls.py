from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Homepage
    path('', views.homepage, name='homepage'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('quick-create-task/', views.quick_create_task, name='quick_create_task'),
    path('tasks/', views.task_list, name='task_list'),
    
    # Add these notification URLs
    path('notifications/clear/', views.clear_all_notifications, name='clear_notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    
    # Task-related URLs
    path('projects/<int:project_id>/tasks/create/', views.task_create, name='task_create'),
    path('projects/<int:project_id>/tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('projects/<int:project_id>/tasks/<int:task_id>/update/', views.task_update, name='task_update'),
    path('projects/<int:project_id>/tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),

    # Team URLs
    path('teams/', views.team_list, name='team_list'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    path('teams/<int:team_id>/projects/', views.team_projects, name='team_projects'),
    path('teams/<int:team_id>/members/view/', views.team_members, name='team_members'),
    path('teams/<int:team_id>/members/manage/', views.manage_team_members, name='manage_team_members'),
    path('teams/<int:team_id>/remove_member/<int:member_id>/', views.remove_team_member, name='remove_team_member'),

    # User authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),

    # Profile-related URLs
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),

    # Progress URLs
    path('progress/', views.progress, name='progress'),
    path('member_progress/', views.member_progress, name='member_progress'),

    # Analytics URL
    path('analytics/', views.analytics_view, name='analytics'),

    # Task status update
    path('update_task_status/<int:task_id>/', views.update_task_status, name='update_task_status'),

    # Settings URLs
    path('settings/', views.settings_view, name='settings'),
    path('settings/change-password/', views.change_password, name='change_password'),

    # Search URL
    path('search/', views.search_view, name='search'),

    # Default Django auth URLs
    path('accounts/', include('django.contrib.auth.urls')),
]