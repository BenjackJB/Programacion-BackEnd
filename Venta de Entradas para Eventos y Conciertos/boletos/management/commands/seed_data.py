"""
Comando de semilla de datos de demostración.

Uso:
    python manage.py seed_data

Crea (de forma idempotente, es decir, se puede ejecutar varias veces):
- Usuarios de prueba con rol Espectador y Organizador.
- Recintos, eventos y sectores/localidades con precios y stock.
- Ejemplos de carrito, pagos, tickets y cambio de estado de órdenes.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from boletos.models import Carro, CarroItem, Compra, Evento, Recinto, Sector, User
from boletos.services import procesar_pago


class Command(BaseCommand):
    """Genera los datos iniciales para probar el sistema."""

    help = 'Carga usuarios, recintos, eventos, sectores y compras de demostración.'

    def handle(self, *args, **options):
        """Ejecuta la carga de datos de demostración."""
        # ---------------------------------------------------------------------
        # 1) USUARIOS (relación 1 a 1 con su carro persistente)
        # ---------------------------------------------------------------------
        organizador, creado = User.objects.get_or_create(
            username='organizador',
            defaults={
                'first_name': 'Laura',
                'last_name': 'Organizadora',
                'email': 'organizador@boletos.cl',
                'rol': User.Rol.ORGANIZADOR,
            },
        )
        if creado:
            organizador.set_password('organizador123')
            organizador.save()

        espectador, creado = User.objects.get_or_create(
            username='espectador',
            defaults={
                'first_name': 'Diego',
                'last_name': 'Espectador',
                'email': 'espectador@boletos.cl',
                'rol': User.Rol.ESPECTADOR,
            },
        )
        if creado:
            espectador.set_password('espectador123')
            espectador.save()

        self.stdout.write('  usuarios: organizador/organizador123 y espectador/espectador123')

        # ---------------------------------------------------------------------
        # 2) RECINTOS
        # ---------------------------------------------------------------------
        recintos = [
            ('Movistar Arena', 'Av. Presidente Kennedy 5735', 'Santiago', 15000),
            ('Estadio Nacional', 'Av. Grecia s/n', 'Santiago', 47000),
            ('Teatro Municipal', 'Isidora Goyenechea 3250', 'Santiago', 2800),
            ('Anfiteatro Cerrado', 'Camino a Melipilla 1250', 'Puente Alto', 8000),
        ]
        recintos_creados = {}
        for nombre, direccion, ciudad, capacidad in recintos:
            recinto, _ = Recinto.all_objects.get_or_create(
                nombre=nombre,
                defaults={
                    'direccion': direccion,
                    'ciudad': ciudad,
                    'capacidad': capacidad,
                    'descripcion': f'Escenario principal: {nombre}.',
                },
            )
            recintos_creados[nombre] = recinto

        # ---------------------------------------------------------------------
        # 3) EVENTOS Y SECTORES (cada sector con su precio y stock propio)
        # ---------------------------------------------------------------------
        base = timezone.now().replace(hour=20, minute=0, second=0, microsecond=0)
        eventos = [
            {
                'nombre': 'Festival Andino 2026',
                'artista': 'Los Cóndores Eléctricos',
                'categoria': Evento.Categoria.FESTIVAL,
                'estado': Evento.Estado.EN_VENTA,
                'fecha': base + timedelta(days=15),
                'recinto': 'Estadio Nacional',
                'imagen_url': '',
                'descripcion': 'Festival de música andina con tres escenarios y feria gastronómica.',
                'sectores': [
                    ('Cancha General', 18000, 500),
                    ('Galería', 32000, 200),
                    ('VIP Frontal', 75000, 60),
                ],
            },
            {
                'nombre': 'Noche de Rock Nacional',
                'artista': 'Banda Ruido Blanco',
                'categoria': Evento.Categoria.CONCIERTO,
                'estado': Evento.Estado.EN_VENTA,
                'fecha': base + timedelta(days=7),
                'recinto': 'Movistar Arena',
                'imagen_url': '',
                'descripcion': 'Gira 2026 con repertorio completo y invitados sorpresa.',
                'sectores': [
                    ('Cancha General', 25000, 300),
                    ('Tribuna Alta', 4000, 150),
                    ('Palco VIP', 120000, 40),
                ],
            },
            {
                'nombre': 'Obra: El Agua y el Fuego',
                'artista': 'Compañía Teatral Sur',
                'categoria': Evento.Categoria.TEATRO,
                'estado': Evento.Estado.PROXIMO,
                'fecha': base + timedelta(days=30),
                'recinto': 'Teatro Municipal',
                'imagen_url': '',
                'descripcion': 'Estreno nacional de la obra ganadora del premio a la mejor dramaturgia.',
                'sectores': [
                    ('Platea Baja', 15000, 120),
                    ('Platea Alta', 9000, 150),
                    ('Balcón', 6000, 60),
                ],
            },
            {
                'nombre': 'Clásico del Estadio',
                'artista': 'Selección Nacional',
                'categoria': Evento.Categoria.DEPORTE,
                'estado': Evento.Estado.FINALIZADO,
                'fecha': base - timedelta(days=20),
                'recinto': 'Estadio Nacional',
                'imagen_url': '',
                'descripcion': 'Partido amistoso de preparación.',
                'sectores': [
                    ('Cancha General', 12000, 400),
                    ('Andes', 20000, 100),
                ],
            },
        ]

        for datos in eventos:
            recinto = recintos_creados[datos.pop('recinto')]
            sectores = datos.pop('sectores')
            evento, _ = Evento.all_objects.get_or_create(
                nombre=datos['nombre'],
                defaults={**datos, 'recinto': recinto, 'organizador': organizador},
            )
            for nombre, precio, stock in sectores:
                Sector.all_objects.get_or_create(
                    evento=evento,
                    nombre=nombre,
                    defaults={'precio': precio, 'stock_total': stock, 'stock_disponible': stock},
                )

        self.stdout.write(f'  eventos: {Evento.objects.count()}  sectores: {Sector.objects.count()}')

        # ---------------------------------------------------------------------
        # 4) EJEMPLO DE COMPRA (carro -> pago -> tickets emitidos)
        # ---------------------------------------------------------------------
        if Compra.objects.filter(comprador=espectador).exists():
            self.stdout.write(self.style.WARNING('  la semilla ya fue ejecutada: no se repite la compra'))
            return

        evento_ejemplo = Evento.objects.get(nombre='Noche de Rock Nacional')
        sector_ejemplo = evento_ejemplo.sectores.get(nombre='Cancha General')

        carro = Carro.obtener_o_crear(espectador)
        CarroItem.objects.create(
            carro=carro,
            sector=sector_ejemplo,
            cantidad=2,
            precio_unitario=sector_ejemplo.precio,
        )

        compra = procesar_pago(espectador, observacion='Compra de demostración (semilla).')
        compra.cambiar_estado(Compra.Estado.ENTREGADO, usuario=organizador, observacion='Ingreso al recinto.')

        self.stdout.write(self.style.SUCCESS(
            f'  compra {str(compra.codigo)[:8]} pagada con {compra.cantidad_tickets} tickets emitidos'
        ))
        self.stdout.write(self.style.SUCCESS('Semilla cargada correctamente.'))
