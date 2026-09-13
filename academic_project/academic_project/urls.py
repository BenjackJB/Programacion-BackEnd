from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from academic.views_jwt import SuperUserTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', SuperUserTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('', include('academic.urls')),
]
