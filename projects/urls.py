from django.urls import path, include  
from . import views
from django.contrib.auth import views as auth_views  

urlpatterns = [
    path('', views.homepage, name='homepage'),  
    path('projects/create/', views.project_create, name='project_create'),  
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),  
    path('projects/<int:project_id>/tasks/create/', views.task_create, name='task_create'),  
    path('projects/<int:project_id>/tasks/<int:task_id>/', views.task_detail, name='task_detail'),  
    path('projects/<int:project_id>/tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),  
    path('teams/<int:team_id>/projects/', views.team_projects, name='team_projects'),  
    
    # Update this to use the custom login view
    path('login/', views.login_view, name='login'),  # <-- Custom login view
    
    path('logout/', auth_views.LogoutView.as_view(), name='logout'), 
    
    path('register/', views.register, name='register'),  
    
    path('accounts/', include('django.contrib.auth.urls')),  # Default auth urls like password reset
]
