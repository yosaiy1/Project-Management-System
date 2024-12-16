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
    path('projects/<int:project_id>/tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),
    path('teams/<int:team_id>/projects/', views.team_projects, name='team_projects'),

    # User authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),

    # Profile-related URLs
    path('profile/update/', views.update_profile, name='update_profile'),  # Profile update
    path('profile/', views.view_profile, name='view_profile'),  # View profile

    # Default Django auth URLs like password reset
    path('accounts/', include('django.contrib.auth.urls')),

    # Optional: Project deletion (if you plan to add this functionality)
    # path('projects/<int:project_id>/delete/', views.project_delete, name='project_delete'),
]
