from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # ADD THIS LINE
    path('', include('app.urls')),
]
