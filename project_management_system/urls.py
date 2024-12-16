from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    # Redirect the root URL to /projects/
    path('', lambda request: HttpResponseRedirect('/projects/')),  
    
    # Admin URL
    path('admin/', admin.site.urls),
    
    # Include project-related URLs
    path('projects/', include('projects.urls')),  
    
    # Default Django auth URLs (login, logout, etc.)
    path('accounts/', include('django.contrib.auth.urls')),  
]

# Serve media files during development (if MEDIA_URL and MEDIA_ROOT are set correctly)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
