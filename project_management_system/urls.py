from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    path('', lambda request: HttpResponseRedirect('/projects/')),  
    path('admin/', admin.site.urls),
    path('projects/', include('projects.urls')),  
    path('accounts/', include('django.contrib.auth.urls')),  
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
