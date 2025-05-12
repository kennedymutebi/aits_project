from django.contrib import admin
from django.conf import settings  # ✅ You need this
from django.conf.urls.static import static
# At the top of your main urls.py file (likely at C:\Users\KENEDDY\aits_project\aits_project\urls.py)


from django.urls import path, include
from apps.authentication import views
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.authentication.urls')),
    path('issues/', include('apps.issues.urls')),
    #path('', include('apps.issues.urls')), 
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # ✅ Add this
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # ✅ Add this
] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
     
