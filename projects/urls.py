from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Homepage and project-related URLs
    path('', views.homepage, name='homepage'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/tasks/create/', views.task_create, name='task_create'),
    path('projects/<int:project_id>/tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('projects/<int:project_id>/tasks/<int:task_id>/update/', views.task_update, name='task_update'),
    path('projects/<int:project_id>/tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),
    
    # Team URLs
    path('teams/', views.team_list, name='team_list'),  # Team list view
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),  # Team detail view
    path('teams/<int:team_id>/projects/', views.team_projects, name='team_projects'),
    path('teams/<int:team_id>/members/view/', views.team_members, name='team_members'),  # Clarified purpose
    path('teams/<int:team_id>/members/manage/', views.manage_team_members, name='manage_team_members'),  # Clarified purpose

    # User authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),

    # Profile-related URLs
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('profile/', views.view_profile, name='view_profile'),

    # Report generation
    path('projects/<int:project_id>/generate_report/', views.generate_report, name='generate_report'),

    # Progress URLs
    path('progress/', views.progress, name='progress'),  # General progress view
    path('member_progress/', views.member_progress, name='member_progress'),

    # Task status update
    path('update_task_status/<int:task_id>/', views.update_task_status, name='update_task_status'),

    # Settings URLs
    path('settings/', views.settings_view, name='settings'),
    path('settings/change-password/', views.change_password, name='change_password'),

    # Default Django auth URLs
    path('accounts/', include('django.contrib.auth.urls')),
]
