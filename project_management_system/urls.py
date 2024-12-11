# urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    path('', lambda request: HttpResponseRedirect('/projects/')),  # Redirect root to /projects/
    path('admin/', admin.site.urls),
    path('projects/', include('projects.urls')),  # Projects URLs are now under /projects/
    # Include Django authentication views
    path('accounts/', include('django.contrib.auth.urls')),  # Default authentication URLs
]

# Add static and media file handling
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
