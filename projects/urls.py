from django.urls import path, include  # Ensure 'include' is imported
from . import views
from django.contrib.auth import views as auth_views  # For login/logout

urlpatterns = [
    path('', views.homepage, name='homepage'),  # Homepage route
    path('projects/create/', views.project_create, name='project_create'),  # Route for creating a project
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),  # Project detail view
    path('projects/<int:project_id>/tasks/create/', views.task_create, name='task_create'),  # Create task view
    path('projects/<int:project_id>/tasks/<int:task_id>/', views.task_detail, name='task_detail'),  # Task detail view
    path('projects/<int:project_id>/tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),  # Task delete view
    path('teams/<int:team_id>/projects/', views.team_projects, name='team_projects'),  # Team projects listing

    # If you want custom login and logout views, keep these, otherwise remove them
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  # Logout view

    # Registration view (optional)
    path('register/', views.register, name='register'),  # Registration view (if implemented)

    # Include Django's built-in authentication URLs
    path('accounts/', include('django.contrib.auth.urls')),  # This includes login, logout, password reset, etc.
]
