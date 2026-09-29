"""
Vistas HTML (templates) del sistema de venta de entradas.

Todas las pantallas son vistas Django que renderizan templates y consumen el
API interno (JSON) mediante JavaScript fetch() con token JWT.

El acceso a las pantallas privadas se valida decodificando el access token
guardado en cookie (`access_token`) al momento de iniciar sesión.
"""

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Evento


# =============================================================================
# UTILIDAD: USUARIO A PARTIR DEL JWT (COOKIE access_token)
# =============================================================================

def obtener_usuario_jwt(request):
    """
    Valida el access token guardado en la cookie `access_token` y devuelve el
    usuario autenticado; devuelve None si no existe, venció o es inválido.
    """
    token = request.COOKIES.get('access_token')
    if not token:
        return None
    try:
        autenticador = JWTAuthentication()
        token_validado = autenticador.get_validated_token(token)
        return autenticador.get_user(token_validado)
    except Exception:
        # Token ausente, vencido, firma inválida o usuario inactivo.
        return None


class MixinContextoJWT:
    """Inyecta el usuario JWT y su rol en el contexto de cada pantalla."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = obtener_usuario_jwt(self.request)
        context['usuario_jwt'] = usuario
        context['es_organizador'] = bool(usuario and usuario.es_organizador)
        if usuario:
            context['nombre_usuario'] = usuario.nombre_completo
        return context


class RequiereSesionJWT(MixinContextoJWT, TemplateView):
    """
    Base de las pantallas privadas: exige un JWT válido y, opcionalmente,
    un rol específico (espectador / organizador).
    """

    rol_requerido = None  # None = cualquier rol autenticado

    def dispatch(self, request, *args, **kwargs):
        usuario = obtener_usuario_jwt(request)
        if usuario is None:
            return redirect(f"{reverse('login')}?next={request.get_full_path()}")

        if self.rol_requerido == 'organizador' and not usuario.es_organizador:
            messages.error(request, 'Esta sección está disponible solo para organizadores de eventos.')
            return redirect('eventos')

        if self.rol_requerido == 'espectador' and usuario.es_organizador:
            messages.error(request, 'Esta sección está disponible solo para espectadores.')
            return redirect('eventos')

        return super().dispatch(request, *args, **kwargs)


# =============================================================================
# AUTENTICACIÓN (PANTALLAS)
# =============================================================================

class LoginView(MixinContextoJWT, TemplateView):
    """Pantalla de inicio de sesión: el formulario llama a POST /api/token/."""

    template_name = 'boletos/login.html'

    def dispatch(self, request, *args, **kwargs):
        # Si ya hay sesión JWT vigente, se redirige al catálogo.
        if obtener_usuario_jwt(request):
            return redirect('eventos')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Iniciar sesión'
        context['next'] = self.request.GET.get('next', '')
        return context


class RegistroView(MixinContextoJWT, TemplateView):
    """Pantalla de registro: el formulario llama a POST /api/registro/."""

    template_name = 'boletos/registro.html'

    def dispatch(self, request, *args, **kwargs):
        if obtener_usuario_jwt(request):
            return redirect('eventos')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear cuenta'
        return context


class LogoutView(View):
    """Cierra la sesión: elimina las cookies JWT y la sesión de Django."""

    def get(self, request, *args, **kwargs):
        logout(request)
        respuesta = redirect('login')
        for cookie in ('access_token', 'refresh_token', 'usuario_nombre', 'usuario_rol'):
            respuesta.delete_cookie(cookie, path='/')
        messages.success(request, 'Has cerrado sesión correctamente.')
        return respuesta

    post = get


# =============================================================================
# CATÁLOGO PÚBLICO
# =============================================================================

class EventosView(MixinContextoJWT, TemplateView):
    """
    Pantalla principal: catálogo de eventos con filtros y búsqueda.
    Los datos se cargan vía JavaScript fetch() desde /api/eventos/.
    """

    template_name = 'boletos/eventos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'titulo': 'Catálogo de eventos',
            'encabezado': 'Eventos y Conciertos',
            'api_endpoint': '/api/eventos/',
        })
        return context


class EventoDetalleView(MixinContextoJWT, TemplateView):
    """Detalle de un evento: información, sectores/localidades y compra."""

    template_name = 'boletos/evento_detalle.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = get_object_or_404(
            Evento.objects.select_related('recinto', 'organizador').filter(activo=True),
            pk=kwargs.get('pk'),
        )
        context.update({
            'titulo': evento.nombre,
            'encabezado': evento.nombre,
            'evento': evento,
            'api_endpoint': f'/api/eventos/{evento.pk}/',
            'api_sectores': f'/api/eventos/{evento.pk}/sectores/',
        })
        return context


# =============================================================================
# PANTALLAS DEL ESPECTADOR
# =============================================================================

class CarroView(RequiereSesionJWT):
    """Carro de compras persistente del espectador."""

    template_name = 'boletos/carro.html'
    rol_requerido = 'espectador'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'titulo': 'Mi carro de compras',
            'encabezado': 'Reserva temporal de entradas',
            'api_endpoint': '/api/carro-tickets/',
        })
        return context


class MisEntradasView(RequiereSesionJWT):
    """Entradas compradas por el espectador (con código Hash/UUID)."""

    template_name = 'boletos/mis_entradas.html'
    rol_requerido = 'espectador'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'titulo': 'Mis entradas',
            'encabezado': 'Entradas compradas',
            'api_endpoint': '/api/mis-entradas/',
        })
        return context


# =============================================================================
# PANTALLAS DEL ORGANIZADOR
# =============================================================================

class OrganizadorEventosView(RequiereSesionJWT):
    """Gestión de eventos y sectores (alta, edición, baja y restauración)."""

    template_name = 'boletos/organizador_eventos.html'
    rol_requerido = 'organizador'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'titulo': 'Gestión de eventos',
            'encabezado': 'Mis eventos',
            'api_endpoint': '/api/eventos/',
        })
        return context


class OrganizadorVentasView(RequiereSesionJWT):
    """Consulta de ventas y cambio de estado de las órdenes."""

    template_name = 'boletos/organizador_ventas.html'
    rol_requerido = 'organizador'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'titulo': 'Ventas y órdenes',
            'encabezado': 'Ventas de entradas',
            'api_endpoint': '/api/compras/',
        })
        return context


class RedireccionInicio(View):
    """La raíz / redirige al catálogo de eventos."""

    def get(self, request, *args, **kwargs):
        return redirect('eventos')
