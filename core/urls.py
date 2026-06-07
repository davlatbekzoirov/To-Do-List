from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('account.urls')),
    path('', include('task.urls')),
    path('', include('notification.urls')),

    path('.well-known/appspecific/com.chrome.devtools.json', lambda r: HttpResponse("{}", content_type="application/json")),
]
