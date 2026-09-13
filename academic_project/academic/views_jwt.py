"""
Vista personalizada para JWT que solo permite superusuarios obtener tokens.
"""
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import PermissionDenied


class SuperUserTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializador que valida que el usuario sea superusuario."""

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_superuser:
            raise PermissionDenied('Solo los superusuarios pueden obtener tokens.')

        return data


class SuperUserTokenObtainPairView(TokenObtainPairView):
    """
    Vista que solo permite a superusuarios obtener tokens JWT.
    POST /api/token/ con {"username": "admin", "password": "admin123"}
    """
    serializer_class = SuperUserTokenObtainPairSerializer
