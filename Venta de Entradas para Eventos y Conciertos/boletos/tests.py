"""
Suite de pruebas del sistema de venta de entradas.

Cobertura por criterio de evaluación:
- Autenticación y autorización JWT con claims de rol.
- Modelo de datos PostgreSQL: CHOICES, relaciones y filtros con django-filter.
- Carro de compras persistente (1 a 1 con el usuario).
- Ciclo de vida de la transacción y descuento/reposición de stock.
- Vistas HTML: pantallas, pie de página del alumno y documentación /docs/.
- Ausencia de admin de Django y de API navegable (solo JSON).
"""

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from . import signals
from .models import Carro, CarroItem, Compra, Evento, Recinto, Sector, Ticket, User
from .services import procesar_pago

CLAVE = 'EntradaSegura2026'
PIE_DE_PAGINA = 'Benjamin Jaque • IEC-N4-C2 • 2026'


def nuevo_cliente():
    """Crea un cliente de pruebas sin credenciales (modo anónimo)."""
    return APIClient()


class BasePruebas(TestCase):
    """Escenario base: usuarios de los dos roles, un evento y un sector."""

    def setUp(self):
        self.organizador = User.objects.create_user(
            username='organiza', password=CLAVE, rol=User.Rol.ORGANIZADOR,
            first_name='Laura', last_name='Organizadora',
        )
        self.organizador2 = User.objects.create_user(
            username='organiza2', password=CLAVE, rol=User.Rol.ORGANIZADOR,
        )
        self.espectador = User.objects.create_user(
            username='especta', password=CLAVE, rol=User.Rol.ESPECTADOR,
            first_name='Diego', last_name='Espectador',
        )
        self.espectador2 = User.objects.create_user(
            username='especta2', password=CLAVE, rol=User.Rol.ESPECTADOR,
        )

        self.recinto = Recinto.objects.create(
            nombre='Movistar Arena', ciudad='Santiago', capacidad=5000
        )
        self.evento = Evento.objects.create(
            nombre='Noche de Rock',
            artista='Banda Ruido Blanco',
            categoria=Evento.Categoria.CONCIERTO,
            estado=Evento.Estado.EN_VENTA,
            fecha=timezone.now() + timedelta(days=10),
            recinto=self.recinto,
            organizador=self.organizador,
            descripcion='Concierto de prueba.',
        )
        self.sector = Sector.objects.create(
            evento=self.evento,
            nombre='Cancha General',
            precio=10000,
            stock_total=50,
            stock_disponible=50,
        )

    # ------------------------------------------------------------------
    # UTILIDADES DE AUTENTICACIÓN JWT
    # ------------------------------------------------------------------

    def obtener_tokens(self, username, password=CLAVE):
        """POST /api/token/ y devuelve la respuesta completa."""
        cliente = nuevo_cliente()
        return cliente.post(
            '/api/token/', {'username': username, 'password': password}, format='json'
        )

    def cliente_jwt(self, user, password=CLAVE):
        """Devuelve un cliente autenticado con el access token del usuario."""
        respuesta = self.obtener_tokens(user.username, password)
        assert respuesta.status_code == status.HTTP_200_OK, respuesta.content
        cliente = nuevo_cliente()
        cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {respuesta.data["access"]}')
        return cliente

    def cliente_con_cookie(self, user, password=CLAVE):
        """Cliente HTML autenticado vía cookie access_token (como hace el frontend)."""
        respuesta = self.obtener_tokens(user.username, password)
        cliente = nuevo_cliente()
        cliente.cookies['access_token'] = respuesta.data['access']
        cliente.cookies['usuario_rol'] = respuesta.data['rol']
        return cliente

    def agregar_al_carro(self, cliente, sector=None, cantidad=1):
        """Ayudante: agrega entradas al carro del usuario autenticado."""
        return cliente.post(
            '/api/carro-tickets/',
            {'sector': (sector or self.sector).pk, 'cantidad': cantidad},
            format='json',
        )


# =============================================================================
# 1. AUTENTICACIÓN Y AUTORIZACIÓN JWT (claims de rol)
# =============================================================================

class AutenticacionJWTTests(BasePruebas):
    """Token access/refresh, claims personalizados de rol y registro."""

    def test_token_incluye_claim_de_rol(self):
        """El payload del JWT debe incluir el rol del usuario (Espectador)."""
        respuesta = self.obtener_tokens('especta')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn('access', respuesta.data)
        self.assertIn('refresh', respuesta.data)
        self.assertEqual(respuesta.data['rol'], 'espectador')

        payload = AccessToken(respuesta.data['access'])
        self.assertEqual(payload['rol'], 'espectador')
        self.assertFalse(payload['es_organizador'])
        self.assertEqual(payload['usuario_id'], self.espectador.pk)
        self.assertEqual(payload['nombre_completo'], 'Diego Espectador')

    def test_token_de_organizador(self):
        """El claim `rol` también identifica al Organizador."""
        respuesta = self.obtener_tokens('organiza')
        payload = AccessToken(respuesta.data['access'])
        self.assertEqual(payload['rol'], 'organizador')
        self.assertTrue(payload['es_organizador'])

    def test_refresh_entrega_nuevo_access(self):
        """POST /api/token/refresh/ renueva el access token."""
        respuesta = self.obtener_tokens('especta')
        refresh = respuesta.data['refresh']
        cliente = nuevo_cliente()
        renovado = cliente.post('/api/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(renovado.status_code, status.HTTP_200_OK)
        self.assertIn('access', renovado.data)

    def test_login_con_credenciales_invalidas(self):
        """Credenciales incorrectas deben rechazarse."""
        cliente = nuevo_cliente()
        respuesta = cliente.post(
            '/api/token/', {'username': 'especta', 'password': 'otra'}, format='json'
        )
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_registro_crea_usuario_y_entrega_token(self):
        """POST /api/registro/ crea usuarios con rol y devuelve los tokens."""
        cliente = nuevo_cliente()
        datos = {
            'username': 'nuevo_usuario',
            'email': 'nuevo@correo.cl',
            'password': CLAVE,
            'first_name': 'Nuevo',
            'last_name': 'Usuario',
            'rol': 'espectador',
        }
        respuesta = cliente.post('/api/registro/', datos, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['rol'], 'espectador')
        self.assertIn('access', respuesta.data)
        usuario = User.objects.get(username='nuevo_usuario')
        self.assertTrue(usuario.check_password(CLAVE))
        self.assertFalse(usuario.es_organizador)

    def test_registro_rechaza_password_corta(self):
        """La contraseña corta debe ser rechazada por el registro."""
        cliente = nuevo_cliente()
        respuesta = cliente.post(
            '/api/registro/',
            {'username': 'otro', 'email': 'o@o.cl', 'password': '123', 'rol': 'espectador'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', respuesta.data)


# =============================================================================
# 2. PERMISOS POR ROL EN LOS ENDPOINTS
# =============================================================================

class PermisosPorRolTests(BasePruebas):
    """La matriz de permisos de la rúbrica aplicada a los endpoints."""

    def test_catalogo_publico_sin_autenticacion(self):
        """GET /api/eventos/ es público (lectura de catálogo)."""
        cliente = nuevo_cliente()
        respuesta = cliente.get('/api/eventos/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['count'], 1)

    def test_sectores_publicos_sin_autenticacion(self):
        """GET /api/eventos/{id}/sectores/ es público."""
        respuesta = nuevo_cliente().get(f'/api/eventos/{self.evento.pk}/sectores/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(respuesta.data[0]['nombre'], 'Cancha General')

    def test_escritura_anonima_rechazada(self):
        """Un anónimo no puede crear eventos ni usar el carro."""
        cliente = nuevo_cliente()
        self.assertIn(
            cliente.post('/api/eventos/', {'nombre': 'X'}, format='json').status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        self.assertIn(
            cliente.get('/api/carro-tickets/').status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_espectador_no_puede_crear_eventos(self):
        """El rol Espectador queda excluido de la gestión de catálogo."""
        cliente = self.cliente_jwt(self.espectador)
        respuesta = cliente.post(
            '/api/eventos/',
            {
                'nombre': 'Intento', 'artista': 'X', 'fecha': '2026-12-31T20:00:00-03:00',
                'recinto': self.recinto.pk,
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizador_crea_evento(self):
        """El rol Organizador sí puede crear eventos (queda como dueño)."""
        cliente = self.cliente_jwt(self.organizador)
        datos = {
            'nombre': 'Nuevo Festival',
            'artista': 'Artista Invitado',
            'categoria': 'festival',
            'estado': 'en_venta',
            'fecha': '2026-12-31T21:00:00-03:00',
            'recinto': self.recinto.pk,
        }
        respuesta = cliente.post('/api/eventos/', datos, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['organizador'], self.organizador.pk)

    def test_organizador_no_edita_eventos_ajenos(self):
        """Un organizador no puede editar (ni borrar) eventos de otro."""
        cliente = self.cliente_jwt(self.organizador2)
        respuesta = cliente.patch(f'/api/eventos/{self.evento.pk}/', {'nombre': 'Hackeado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        borrado = cliente.delete(f'/api/eventos/{self.evento.pk}/')
        self.assertEqual(borrado.status_code, status.HTTP_403_FORBIDDEN)

    def test_solo_organizador_cambia_estado_de_compra(self):
        """PATCH /api/compras/{id}/estado/ exige rol Organizador."""
        cliente_esp = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente_esp, cantidad=1)
        compra = procesar_pago(self.espectador)

        self.assertEqual(
            cliente_esp.patch(
                f'/api/compras/{compra.pk}/estado/', {'estado': 'CANCELADO'}, format='json'
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        cliente_org = self.cliente_jwt(self.organizador)
        respuesta = cliente_org.patch(
            f'/api/compras/{compra.pk}/estado/', {'estado': 'ENTREGADO'}, format='json'
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_espectador_no_puede_ver_las_ventas_de_otros(self):
        """GET /api/compras/ devuelve solo las órdenes propias al espectador."""
        cliente_esp = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente_esp, cantidad=2)
        procesar_pago(self.espectador)

        otra = self.cliente_jwt(self.espectador2)
        self.assertEqual(otra.get('/api/compras/').data['count'], 0)
        self.assertEqual(cliente_esp.get('/api/compras/').data['count'], 1)
        self.assertEqual(
            self.cliente_jwt(self.organizador).get('/api/compras/').data['count'], 1
        )


# =============================================================================
# 3. MODELO DE DATOS: CHOICES, RELACIONES Y FILTROS
# =============================================================================

class ModeloYFiltrosTests(BasePruebas):
    """CHOICES, relaciones ForeignKey/OneToOne y sistema de filtros."""

    def test_modelos_declaran_choices(self):
        """Exigido por la rúbrica: propiedades CHOICES en los modelos."""
        self.assertTrue(Compra._meta.get_field('estado').choices)
        self.assertTrue(Evento._meta.get_field('categoria').choices)
        self.assertTrue(Evento._meta.get_field('estado').choices)
        self.assertTrue(Ticket._meta.get_field('estado').choices)
        self.assertTrue(User._meta.get_field('rol').choices)
        estados = dict(Compra._meta.get_field('estado').choices)
        self.assertIn('PAGADO', estados)
        self.assertIn('CANCELADO', estados)

    def test_relaciones_de_integridad(self):
        """ForeignKeys y OneToOne referenciadas (Evento->Recinto, Carro->User)."""
        self.assertEqual(self.evento.recinto_id, self.recinto.pk)
        self.assertEqual(self.sector.evento_id, self.evento.pk)
        carro = Carro.obtener_o_crear(self.espectador)
        self.assertEqual(carro.usuario_id, self.espectador.pk)
        # Relación 1 a 1: no se crea un segundo carro para el mismo usuario.
        self.assertEqual(Carro.objects.filter(usuario=self.espectador).count(), 1)

    def test_filtro_por_categoria(self):
        """django-filter: filtrado por categoría."""
        festival = Evento.objects.create(
            nombre='Festival Prueba', artista='X', categoria=Evento.Categoria.FESTIVAL,
            fecha=timezone.now() + timedelta(days=20), recinto=self.recinto,
            organizador=self.organizador,
        )
        Sector.objects.create(
            evento=festival, nombre='VIP', precio=50000, stock_total=10, stock_disponible=10
        )
        cliente = nuevo_cliente()

        respuesta = cliente.get('/api/eventos/', {'categoria': 'concierto'})
        self.assertEqual(respuesta.data['count'], 1)
        self.assertEqual(respuesta.data['results'][0]['nombre'], 'Noche de Rock')

        respuesta = cliente.get('/api/eventos/', {'categoria': 'festival'})
        self.assertEqual(respuesta.data['count'], 1)
        self.assertEqual(respuesta.data['results'][0]['nombre'], 'Festival Prueba')

    def test_filtro_por_rango_de_precios(self):
        """django-filter: rango de precios según el sector más barato."""
        caro = Evento.objects.create(
            nombre='Evento Caro', artista='Y', categoria=Evento.Categoria.CONCIERTO,
            fecha=timezone.now() + timedelta(days=25), recinto=self.recinto,
            organizador=self.organizador,
        )
        Sector.objects.create(
            evento=caro, nombre='Palco', precio=150000, stock_total=20, stock_disponible=20
        )
        cliente = nuevo_cliente()

        baratos = cliente.get('/api/eventos/', {'precio_max': 20000})
        self.assertEqual(baratos.data['count'], 1)
        self.assertEqual(baratos.data['results'][0]['nombre'], 'Noche de Rock')

        caros = cliente.get('/api/eventos/', {'precio_min': 100000})
        self.assertEqual(caros.data['count'], 1)
        self.assertEqual(caros.data['results'][0]['nombre'], 'Evento Caro')

    def test_busqueda_y_ordenamiento(self):
        """SearchFilter y OrderingFilter sobre campos clave."""
        cliente = nuevo_cliente()
        respuesta = cliente.get('/api/eventos/', {'search': 'Ruido Blanco'})
        self.assertEqual(respuesta.data['count'], 1)

        respuesta = cliente.get('/api/eventos/', {'search': 'zzz-inexistente'})
        self.assertEqual(respuesta.data['count'], 0)

        ordenado = cliente.get('/api/eventos/', {'ordering': '-fecha'})
        self.assertEqual(ordenado.data['results'][0]['nombre'], 'Noche de Rock')

    def test_filtro_de_compras_por_estado(self):
        """django-filter aplicado a la consulta de ventas del organizador."""
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=1)
        procesar_pago(self.espectador)

        organizador = self.cliente_jwt(self.organizador)
        self.assertEqual(organizador.get('/api/compras/', {'estado': 'PAGADO'}).data['count'], 1)
        self.assertEqual(organizador.get('/api/compras/', {'estado': 'CANCELADO'}).data['count'], 0)

    def test_paginacion(self):
        """El listado de eventos pagina con PAGE_SIZE = 20."""
        for i in range(22):
            evento = Evento.objects.create(
                nombre=f'Evento {i}', artista='Varios', categoria=Evento.Categoria.OTRO,
                fecha=timezone.now() + timedelta(days=30 + i), recinto=self.recinto,
                organizador=self.organizador,
            )
            Sector.objects.create(
                evento=evento, nombre='General', precio=5000, stock_total=5, stock_disponible=5
            )
        respuesta = nuevo_cliente().get('/api/eventos/')
        self.assertEqual(respuesta.data['count'], 23)
        self.assertEqual(len(respuesta.data['results']), 20)
        self.assertIsNotNone(respuesta.data['next'])


# =============================================================================
# 4. CARRO DE COMPRAS PERSISTENTE
# =============================================================================

class CarroPersistenteTests(BasePruebas):
    """Relación 1 a 1, persistencia tras logout y control de duplicados."""

    def test_agregar_y_leer_carro(self):
        """POST /api/carro-tickets/ crea ítems y el GET los devuelve con total."""
        cliente = self.cliente_jwt(self.espectador)
        respuesta = self.agregar_al_carro(cliente, cantidad=3)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['cantidad_entradas'], 3)
        self.assertEqual(float(respuesta.data['total']), 30000)

        detalle = cliente.get('/api/carro-tickets/')
        self.assertEqual(detalle.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detalle.data['items']), 1)
        self.assertEqual(detalle.data['items'][0]['sector'], self.sector.pk)

    def test_carro_persiste_tras_cerrar_sesion(self):
        """Los ítems se conservan al "cerrar sesión" e iniciar desde otro cliente."""
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=2)

        # Simula logout + login desde otro dispositivo (credenciales nuevas).
        otro = self.cliente_jwt(self.espectador)
        detalle = otro.get('/api/carro-tickets/')
        self.assertEqual(detalle.data['cantidad_entradas'], 2)
        self.assertEqual(Carro.objects.filter(usuario=self.espectador).count(), 1)

    def test_no_se_permiten_duplicados_del_mismo_sector(self):
        """Repetir el mismo sector suma la cantidad en lugar de duplicar ítems."""
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=2)
        respuesta = self.agregar_al_carro(cliente, cantidad=3)
        self.assertEqual(len(respuesta.data['items']), 1)
        self.assertEqual(respuesta.data['items'][0]['cantidad'], 5)

    def test_eliminar_item_y_vaciar_carro(self):
        """DELETE individual y DELETE total del carro."""
        cliente = self.cliente_jwt(self.espectador)
        respuesta = self.agregar_al_carro(cliente, cantidad=1)
        item_id = respuesta.data['items'][0]['id']

        borrado = cliente.delete(f'/api/carro-tickets/{item_id}/')
        self.assertEqual(borrado.status_code, status.HTTP_200_OK)
        self.assertEqual(borrado.data['items'], [])

        self.agregar_al_carro(cliente, cantidad=2)
        vaciado = cliente.delete('/api/carro-tickets/')
        self.assertEqual(vaciado.data['items'], [])
        self.assertEqual(CarroItem.all_objects.filter(carro__usuario=self.espectador).count(), 0)

    def test_agregar_al_carro_no_descuenta_stock(self):
        """Regla de negocio: el stock NO se descuenta al agregar al carro."""
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=10)
        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 50)
        self.assertEqual(Compra.objects.count(), 0)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_carro_de_un_usuario_no_visible_en_otro(self):
        """Cada usuario solo ve su propio carro (relación 1 a 1)."""
        self.agregar_al_carro(self.cliente_jwt(self.espectador), cantidad=1)
        ajeno = self.cliente_jwt(self.espectador2).get('/api/carro-tickets/')
        self.assertEqual(ajeno.data['items'], [])
        self.assertEqual(ajeno.data['total'], '0')


# =============================================================================
# 5. TRANSACCIONES, STOCK Y CICLO DE VIDA DE LA ORDEN
# =============================================================================

class TransaccionesYStockTests(BasePruebas):
    """Checkout, descuento al PAGADO, reposición al CANCELADO y tickets."""

    def pagar(self, cantidad=2):
        """Ayudante: agrega al carro y ejecuta el checkout."""
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=cantidad)
        return cliente.post('/api/compras/pagar/', {}, format='json')

    def test_pago_descuenta_stock_y_emite_tickets(self):
        """El pago pasa la orden a PAGADO, descuenta stock y emite tickets únicos."""
        respuesta = self.pagar(cantidad=3)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['estado'], 'PAGADO')
        self.assertEqual(respuesta.data['cantidad_tickets'], 3)
        self.assertIsNotNone(respuesta.data['fecha_pago'])

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 47)

        codigos = [t['codigo'] for t in respuesta.data['tickets']]
        self.assertEqual(len(codigos), 3)
        self.assertEqual(len(set(codigos)), 3)  # código Hash/UUID único por ticket
        for codigo in codigos:
            self.assertEqual(len(codigo), 32)

        # El carro queda liquidado tras confirmar el pedido.
        self.assertEqual(CarroItem.all_objects.filter(carro__usuario=self.espectador).count(), 0)

    def test_carro_vacio_no_permite_pagar(self):
        """El checkout rechaza carros vacíos."""
        cliente = self.cliente_jwt(self.espectador)
        respuesta = cliente.post('/api/compras/pagar/', {}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Compra.objects.count(), 0)

    def test_stock_insuficiente_rechaza_la_transaccion(self):
        """Si no hay cupos, el pago se rechaza y no cambia nada."""
        Sector.objects.filter(pk=self.sector.pk).update(stock_total=2, stock_disponible=2)
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=10)

        respuesta = cliente.post('/api/compras/pagar/', {}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('stock', respuesta.data)

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 2)   # sin descuento
        self.assertEqual(Compra.objects.count(), 0)          # sin orden huérfana
        self.assertEqual(Ticket.objects.count(), 0)

    def test_cancelar_repone_stock_y_anula_tickets(self):
        """CANCELADO repone el stock descontado y anula los tickets."""
        self.pagar(cantidad=4)
        compra = Compra.objects.get(comprador=self.espectador)
        organizador = self.cliente_jwt(self.organizador)

        respuesta = organizador.patch(
            f'/api/compras/{compra.pk}/estado/',
            {'estado': 'CANCELADO', 'observacion': 'Evento suspendido'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['estado'], 'CANCELADO')

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 50)  # stock repuesto
        self.assertEqual(
            set(compra.tickets.values_list('estado', flat=True)), {Ticket.Estado.CANCELADO}
        )

    def test_entregar_marca_asistencia(self):
        """ENTREGADO marca los tickets como ingresados (asistencia)."""
        self.pagar(cantidad=2)
        compra = Compra.objects.get(comprador=self.espectador)
        organizador = self.cliente_jwt(self.organizador)

        respuesta = organizador.patch(
            f'/api/compras/{compra.pk}/estado/', {'estado': 'ENTREGADO'}, format='json'
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(compra.tickets.values_list('estado', flat=True)), {Ticket.Estado.INGRESADO}
        )
        # El stock NO se repone al entregar: la venta se concreta.
        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 48)

    def test_transiciones_de_estado_invalidas(self):
        """Se respeta el ciclo PENDIENTE -> PAGADO -> ENTREGADO/CANCELADO."""
        self.pagar(cantidad=1)
        compra = Compra.objects.get(comprador=self.espectador)
        organizador = self.cliente_jwt(self.organizador)

        organizador.patch(f'/api/compras/{compra.pk}/estado/', {'estado': 'ENTREGADO'}, format='json')
        # De ENTREGADO ya no se puede volver atrás.
        invalida = organizador.patch(
            f'/api/compras/{compra.pk}/estado/', {'estado': 'CANCELADO'}, format='json'
        )
        self.assertEqual(invalida.status_code, status.HTTP_400_BAD_REQUEST)
        compra.refresh_from_db()
        self.assertEqual(compra.estado, 'ENTREGADO')

    def test_historial_registra_las_transiciones(self):
        """Cada cambio de estado queda auditado en CompraHistorial."""
        self.pagar(cantidad=1)
        compra = Compra.objects.get(comprador=self.espectador)
        self.cliente_jwt(self.organizador).patch(
            f'/api/compras/{compra.pk}/estado/', {'estado': 'ENTREGADO'}, format='json'
        )
        estados = list(compra.historial.values_list('estado', flat=True))
        self.assertEqual(estados, ['PENDIENTE', 'PAGADO', 'ENTREGADO'])

    def test_reposicion_libera_stock_para_nueva_compra(self):
        """Tras cancelar, el stock vuelve a estar disponible para otro usuario."""
        self.pagar(cantidad=5)
        compra = Compra.objects.get(comprador=self.espectador)
        self.cliente_jwt(self.organizador).patch(
            f'/api/compras/{compra.pk}/estado/', {'estado': 'CANCELADO'}, format='json'
        )

        otro = self.cliente_jwt(self.espectador2)
        self.agregar_al_carro(otro, cantidad=5)
        pago = otro.post('/api/compras/pagar/', {}, format='json')
        self.assertEqual(pago.status_code, status.HTTP_201_CREATED)


# =============================================================================
# 6. MIS ENTRADAS
# =============================================================================

class MisEntradasTests(BasePruebas):
    """GET /api/mis-entradas/ devuelve solo las entradas del usuario."""

    def test_mis_entradas_tras_el_pago(self):
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=2)
        cliente.post('/api/compras/pagar/', {}, format='json')

        respuesta = cliente.get('/api/mis-entradas/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['count'], 2)
        entrada = respuesta.data['results'][0]
        self.assertEqual(entrada['evento']['nombre'], 'Noche de Rock')
        self.assertEqual(entrada['sector_nombre'], 'Cancha General')
        self.assertEqual(entrada['estado'], 'VALIDO')

    def test_no_ve_entradas_de_otros(self):
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=1)
        cliente.post('/api/compras/pagar/', {}, format='json')

        ajeno = self.cliente_jwt(self.espectador2).get('/api/mis-entradas/')
        self.assertEqual(ajeno.data['count'], 0)

    def test_organizador_no_usa_mis_entradas(self):
        """El endpoint es exclusivo del rol Espectador (matriz de permisos)."""
        respuesta = self.cliente_jwt(self.organizador).get('/api/mis-entradas/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


# =============================================================================
# 7. VISTAS HTML, PIE DE PÁGINA Y DOCUMENTACIÓN
# =============================================================================

class VistasHTMLTests(BasePruebas):
    """Pantallas del sistema: accesibilidad, pie de página y documentación."""

    PANTALLAS_PUBLICAS = ['eventos', 'login', 'registro']

    def test_catalogo_se_renderiza(self):
        respuesta = nuevo_cliente().get(reverse('eventos'))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        # El catálogo es una pantalla que consume /api/eventos/ desde JavaScript.
        self.assertContains(respuesta, 'id="gridEventos"', status_code=200)
        self.assertContains(respuesta, '/api/eventos/', status_code=200)

    def test_detalle_de_evento(self):
        respuesta = nuevo_cliente().get(reverse('evento-detalle', args=[self.evento.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertContains(respuesta, 'Banda Ruido Blanco', html=False, status_code=200)

    def test_detalle_inexistente_devuelve_404(self):
        respuesta = nuevo_cliente().get(reverse('evento-detalle', args=[999]))
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_pantallas_privadas_redirigen_a_login(self):
        """Las pantallas del espectador/organizador exigen sesión JWT."""
        for nombre in ('carro', 'mis-entradas', 'organizador-eventos', 'organizador-ventas'):
            respuesta = nuevo_cliente().get(reverse(nombre))
            self.assertEqual(respuesta.status_code, status.HTTP_302_FOUND, nombre)
            self.assertIn('/login/', respuesta.url, nombre)

    def test_espectador_no_entra_a_pantallas_de_organizador(self):
        cliente = self.cliente_con_cookie(self.espectador)
        respuesta = cliente.get(reverse('organizador-eventos'))
        self.assertEqual(respuesta.status_code, status.HTTP_302_FOUND)
        self.assertEqual(respuesta.url, reverse('eventos'))

    def test_pantallas_de_organizador_se_renderizan(self):
        cliente = self.cliente_con_cookie(self.organizador)
        for nombre in ('organizador-eventos', 'organizador-ventas'):
            respuesta = cliente.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK, nombre)

    def test_pantallas_de_espectador_se_renderizan(self):
        cliente = self.cliente_con_cookie(self.espectador)
        for nombre in ('carro', 'mis-entradas'):
            respuesta = cliente.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK, nombre)

    def test_toda_pantalla_muestra_los_datos_del_alumno(self):
        """Pie de página con Nombre • Sección • Año en todas las pantallas."""
        cliente = self.cliente_con_cookie(self.espectador)
        organizador = self.cliente_con_cookie(self.organizador)
        url_args = {
            'eventos': (nuevo_cliente(), reverse('eventos')),
            'login': (nuevo_cliente(), reverse('login')),
            'registro': (nuevo_cliente(), reverse('registro')),
            'detalle': (nuevo_cliente(), reverse('evento-detalle', args=[self.evento.pk])),
            'carro': (cliente, reverse('carro')),
            'mis-entradas': (cliente, reverse('mis-entradas')),
            'organizador-eventos': (organizador, reverse('organizador-eventos')),
            'organizador-ventas': (organizador, reverse('organizador-ventas')),
            'logout': (nuevo_cliente(), reverse('logout')),
        }
        for nombre, (cliente_pantalla, url) in url_args.items():
            respuesta = cliente_pantalla.get(url, follow=True)
            contenido = respuesta.content.decode()
            self.assertIn(PIE_DE_PAGINA, contenido, f'Falta pie de página en {nombre}')
            self.assertIn('/docs/', contenido, f'Falta enlace a documentación en {nombre}')

    def test_ninguna_pantalla_muestra_comentarios_de_plantilla(self):
        """Los comentarios {# #} de Django nunca deben verse en pantalla.

        Un comentario `{# ... #}` escrito en varias líneas no lo reconoce el
        motor de plantillas y el texto se filtra al usuario: esta prueba evita
        que vuelva a ocurrir en cualquiera de las pantallas.
        """
        cliente = self.cliente_con_cookie(self.espectador)
        organizador = self.cliente_con_cookie(self.organizador)
        pantallas = {
            'eventos': (nuevo_cliente(), reverse('eventos')),
            'login': (nuevo_cliente(), reverse('login')),
            'registro': (nuevo_cliente(), reverse('registro')),
            'detalle': (nuevo_cliente(), reverse('evento-detalle', args=[self.evento.pk])),
            'carro': (cliente, reverse('carro')),
            'mis-entradas': (cliente, reverse('mis-entradas')),
            'organizador-eventos': (organizador, reverse('organizador-eventos')),
            'organizador-ventas': (organizador, reverse('organizador-ventas')),
        }
        for nombre, (cliente_pantalla, url) in pantallas.items():
            contenido = cliente_pantalla.get(url, follow=True).content.decode()
            self.assertNotIn('{#', contenido, f'Comentario de plantilla visible en {nombre}')
            self.assertNotIn(
                'El JS rellena este contenedor', contenido,
                f'Comentario filtrado en {nombre}',
            )

    def test_logout_elimina_las_cookies_de_sesion(self):
        cliente = self.cliente_con_cookie(self.espectador)
        respuesta = cliente.get(reverse('logout'))
        self.assertEqual(respuesta.status_code, status.HTTP_302_FOUND)
        # Las cookies JWT quedan borradas (valor vacío) tras el cierre de sesión.
        self.assertEqual(cliente.cookies['access_token'].value, '')
        self.assertEqual(cliente.cookies['refresh_token'].value, '')

    def test_documentacion_swagger_disponible(self):
        """Footer -> /docs/ (Swagger/OpenAPI) y esquema /api/schema/."""
        self.assertEqual(nuevo_cliente().get('/docs/').status_code, status.HTTP_200_OK)
        esquema = nuevo_cliente().get('/api/schema/')
        self.assertEqual(esquema.status_code, status.HTTP_200_OK)
        self.assertIn(b'eventos', esquema.content)

    def test_documentacion_incluye_datos_del_alumno(self):
        """La documentación de la API también identifica al alumno y la sección."""
        esquema = nuevo_cliente().get('/api/schema/').content.decode()
        self.assertIn('Benjamin Jaque', esquema)
        self.assertIn('IEC-N4-C2', esquema)
        self.assertIn('2026', esquema)

    def test_enlace_falso_o_roto_redirige_al_inicio(self):
        """Red de seguridad con re_path: una URL inexistente manda al catálogo."""
        respuesta = nuevo_cliente().get('/pagina-que-no-existe/')
        self.assertEqual(respuesta.status_code, status.HTTP_302_FOUND)
        self.assertEqual(respuesta.url, reverse('eventos'))

    def test_enlace_roto_conserva_la_consulta(self):
        """La red de seguridad mantiene los parámetros de la dirección original."""
        respuesta = nuevo_cliente().get('/enlace-viejo/subpágina/?search=rock')
        self.assertEqual(respuesta.status_code, status.HTTP_302_FOUND)
        self.assertIn('search=rock', respuesta.url)

    def test_el_api_no_usa_la_red_de_seguridad(self):
        """Una ruta falsa del API sigue respondiendo 404 (nunca HTML redirigido)."""
        respuesta = nuevo_cliente().get('/api/ruta-inexistente/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 8. RESTRICCIONES DE ARQUITECTURA (sin admin ni API navegable)
# =============================================================================

class RestriccionesArquitecturaTests(BasePruebas):
    """Sin admin de Django, sin API navegable: solo vistas + JSON."""

    def test_no_existe_admin_de_django(self):
        """La URL /admin/ no está registrada en el proyecto."""
        respuesta = nuevo_cliente().get('/admin/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_solo_responde_json(self):
        """El API no expone render HTML (API browsable deshabilitada)."""
        respuesta = nuevo_cliente().get('/api/eventos/', HTTP_ACCEPT='text/html')
        # Sin renderer HTML disponible, DRF rechaza la petición (406) en lugar
        # de servir una página navegable del API.
        self.assertEqual(respuesta.status_code, status.HTTP_406_NOT_ACCEPTABLE)
        self.assertFalse(respuesta['Content-Type'].startswith('text/html'))
        # Con Accept JSON responde normalmente.
        ok = nuevo_cliente().get('/api/eventos/', HTTP_ACCEPT='application/json')
        self.assertTrue(ok['Content-Type'].startswith('application/json'))

    def test_no_existe_indice_navegable_del_api(self):
        """No hay vista directa al API: /api/ raíz no existe."""
        respuesta = nuevo_cliente().get('/api/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_eliminar_evento_es_borrado_logico(self):
        """El borrado físico no existe: se marca activo=False."""
        cliente = self.cliente_jwt(self.organizador)
        respuesta = cliente.delete(f'/api/eventos/{self.evento.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.evento.refresh_from_db()
        self.assertFalse(self.evento.activo)
        self.assertEqual(Evento.objects.count(), 0)          # ocultos para el público
        self.assertEqual(Evento.all_objects.count(), 1)      # visibles para gestión

        restaurado = cliente.post(f'/api/eventos/{self.evento.pk}/restaurar/')
        self.assertEqual(restaurado.status_code, status.HTTP_200_OK)
        self.evento.refresh_from_db()
        self.assertTrue(self.evento.activo)


# =============================================================================
# 9. SEÑALES DE DJANGO (boletos/signals.py)
# =============================================================================

class SenalesDeTransicionTests(BasePruebas):
    """Los efectos de cada transición de estado los ejecutan las señales."""

    def pagar(self, cantidad=2):
        """Ayudante: agrega al carro y ejecuta el checkout."""
        cliente = self.cliente_jwt(self.espectador)
        self.agregar_al_carro(cliente, cantidad=cantidad)
        return cliente.post('/api/compras/pagar/', {}, format='json')

    def test_las_receptores_estan_conectadas(self):
        """`apps.ready()` conecta las dos receptores de Compra de signals.py."""

        def receptores(senal):
            """Aplana los receptores vivos de la señal para la clase Compra."""
            return [funcion for grupo in senal._live_receivers(Compra) for funcion in grupo]

        self.assertIn(signals.capturar_estado_anterior, receptores(signals.pre_save))
        self.assertIn(signals.aplicar_efectos_de_transicion, receptores(signals.post_save))

    def test_pago_dispara_la_senal_de_emision(self):
        """PAGADO: la señal descuenta el stock y emite los tickets Hash/UUID."""
        with mock.patch.object(signals, '_pagar_orden', wraps=signals._pagar_orden) as espia:
            respuesta = self.pagar(cantidad=3)
            self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
            espia.assert_called_once()

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 47)
        self.assertEqual(Ticket.objects.count(), 3)

    def test_reguardar_sin_transicion_no_repite_el_efecto(self):
        """Idempotencia: un save extra de la orden PAGADO no vende dos veces."""
        self.pagar(cantidad=2)
        compra = Compra.objects.get(comprador=self.espectador)

        with mock.patch.object(signals, '_pagar_orden', wraps=signals._pagar_orden) as espia:
            compra.save()  # mismo estado: la señal no debe actuar
            espia.assert_not_called()

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 48)
        self.assertEqual(Ticket.objects.count(), 2)

    def test_cancelar_dispara_la_senal_de_reposicion(self):
        """CANCELADO: la señal repone el stock y anula los tickets una sola vez."""
        self.pagar(cantidad=4)
        compra = Compra.objects.get(comprador=self.espectador)
        organizador = self.cliente_jwt(self.organizador)

        with mock.patch.object(signals, '_cancelar_orden', wraps=signals._cancelar_orden) as espia:
            respuesta = organizador.patch(
                f'/api/compras/{compra.pk}/estado/',
                {'estado': 'CANCELADO', 'observacion': 'Prueba de señales'},
                format='json',
            )
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
            self.assertEqual(espia.call_count, 1)

        # Un guardado posterior con el mismo estado no vuelve a sumar cupos.
        compra.observacion = 'observación extra'
        compra.save()
        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 50)
        self.assertEqual(
            set(compra.tickets.values_list('estado', flat=True)), {Ticket.Estado.CANCELADO}
        )

    def test_entregar_dispara_la_senal_de_asistencia(self):
        """ENTREGADO: la señal marca los tickets como ingresados (sin reposición)."""
        self.pagar(cantidad=2)
        compra = Compra.objects.get(comprador=self.espectador)
        organizador = self.cliente_jwt(self.organizador)

        with mock.patch.object(signals, '_entregar_orden', wraps=signals._entregar_orden) as espia:
            respuesta = organizador.patch(
                f'/api/compras/{compra.pk}/estado/', {'estado': 'ENTREGADO'}, format='json'
            )
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
            self.assertEqual(espia.call_count, 1)

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.stock_disponible, 48)  # venta concreta
        self.assertEqual(
            set(compra.tickets.values_list('estado', flat=True)), {Ticket.Estado.INGRESADO}
        )
