"""
Script de sembrado de datos — Dulce Arte.
Crea usuarios, categorías, insumos, productos (BOM), clientes y pedidos.

Uso:  python seed_data.py
"""
from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dulce_arte.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.utils import timezone  # noqa: E402

from core.models import (  # noqa: E402
    Categoria,
    Cliente,
    ComponenteProducto,
    Despacho,
    DetallePedido,
    Insumo,
    Perfil,
    Pedido,
    Producto,
)
from core.precios_referencia import PRECIOS_CLP  # noqa: E402


def f(v):
    return Decimal(str(v))


def main() -> None:
    print("== Sembrando Dulce Arte ==")

    # --- Usuarios ---------------------------------------------------------
    if not User.objects.filter(username="admin").exists():
        admin = User.objects.create_superuser("admin", "admin@dulcearte.cl", "admin1234")
        Perfil.objects.get_or_create(user=admin, defaults={"rol": Perfil.Rol.ADMIN})
        print("  ✓ superusuario admin / admin1234")

    for username, rol, nombre in [
        ("cocina", Perfil.Rol.COCINA, "Jefa de Cocina"),
        ("despacho", Perfil.Rol.DESPACHO, "Repartidor"),
        ("ventas", Perfil.Rol.VENTA, "Vendedora"),
    ]:
        if not User.objects.filter(username=username).exists():
            u = User.objects.create_user(username, f"{username}@dulcearte.cl", "demo1234")
            u.first_name = nombre
            u.save()
            Perfil.objects.get_or_create(user=u, defaults={"rol": rol})
            print(f"  ✓ usuario {username} / demo1234")

    admin_user = User.objects.get(username="admin")

    # --- Categorías -------------------------------------------------------
    cats = {}
    for nombre, desc in [
        ("Tortas", "Tortas personalizadas por capas y decoración"),
        ("Cupcakes", "Cupcakes individuales y cajas surtidas"),
        ("Galletas", "Galletas decoradas y saladas"),
        ("Postres", "Porciones individuales, milhojas y éclairs"),
    ]:
        cats[nombre], _ = Categoria.objects.get_or_create(
            nombre=nombre, defaults={"descripcion": desc}
        )
    print(f"  ✓ {len(cats)} categorías")

    # --- Insumos ----------------------------------------------------------
    # Los precios viven en core/precios_referencia.py (CLP por unidad de medida).
    insumos = {}
    datos_insumos = [
        ("Harina", "kg", 120, 20, "Molino Los Ángeles"),
        ("Azúcar", "kg", 80, 15, "Dulcesa"),
        ("Mantequilla", "kg", 25, 10, "Lácteos Sur"),
        ("Huevos", "und", 300, 60, "Campo Verde"),
        ("Chocolate amargo", "kg", 15, 8, "Cacao Andino"),
        ("Crema para batir", "l", 30, 10, "Lácteos Sur"),
        ("Fondant", "kg", 10, 5, "Pastelera Ltda"),
        ("Colorante alimentario", "ml", 500, 100, "Pastelera Ltda"),
        ("Frutas frescas", "kg", 18, 6, "Feria Central"),
        ("Levadura", "kg", 5, 2, "Molino Los Ángeles"),
        ("Cacao en polvo", "kg", 8, 3, "Cacao Andino"),
        ("Vainilla", "ml", 400, 80, "Pastelera Ltda"),
        ("Cajas de presentación", "und", 60, 25, "Empaques RM"),
        ("Faja para torta", "und", 40, 15, "Empaques RM"),
    ]
    for nombre, unidad, stock, minimo, prov in datos_insumos:
        precio = PRECIOS_CLP[nombre][0]
        insumo, created = Insumo.objects.get_or_create(
            nombre=nombre,
            defaults={
                "unidad": unidad,
                "stock_actual": f(stock),
                "stock_minimo": f(minimo),
                "precio_unitario": precio,
                "proveedor": prov,
            },
        )
        # Idempotente: corrige precios viejos aunque el insumo ya exista.
        if not created and insumo.precio_unitario != precio:
            insumo.precio_unitario = precio
            insumo.save(update_fields=["precio_unitario", "actualizado"])
        insumos[nombre] = insumo
    print(f"  ✓ {len(insumos)} insumos")

    # --- Productos + BOM --------------------------------------------------
    catalogo = [
        # (nombre, categoria, precio, emoji, descripcion, [(insumo, cant), ...])
        ("Torta de Chocolate 3 capas", "Tortas", 32000, "🍫",
         "Torta de chocolate amargo con relleno de ganache y cobertura en ganache esculpida.",
         [("Harina", 1.2), ("Azúcar", 0.9), ("Mantequilla", 0.6), ("Huevos", 8),
          ("Chocolate amargo", 0.8), ("Cacao en polvo", 0.2), ("Levadura", 0.05),
          ("Vainilla", 10), ("Cajas de presentación", 1)]),

        ("Torta de Frambuesa", "Tortas", 29000, "🍓",
         "Bizcocho de vainilla con crema y frambuesas frescas, decoración rústica.",
         [("Harina", 1.0), ("Azúcar", 0.7), ("Mantequilla", 0.5), ("Huevos", 6),
          ("Crema para batir", 0.6), ("Frutas frescas", 0.5), ("Vainilla", 8),
          ("Cajas de presentación", 1)]),

        ("Torta Boda Fondant", "Tortas", 85000, "💒",
         "Torta de 3 pisos cubierta con fondant blanco y flores de azúcar.",
         [("Harina", 3.0), ("Azúcar", 2.0), ("Mantequilla", 1.5), ("Huevos", 18),
          ("Fondant", 2.5), ("Crema para batir", 1.0), ("Vainilla", 20),
          ("Faja para torta", 4), ("Cajas de presentación", 2)]),

        ("Caja 12 Cupcakes", "Cupcakes", 18000, "🧁",
         "Doce cupcakes surtidos con buttercream y decoración a elección.",
         [("Harina", 0.7), ("Azúcar", 0.6), ("Mantequilla", 0.5), ("Huevos", 5),
          ("Crema para batir", 0.4), ("Colorante alimentario", 30),
          ("Vainilla", 8), ("Cajas de presentación", 1)]),

        ("Cupcake Van individually", "Cupcakes", 2200, "🧁",
         "Cupcake individual de vainilla con cobertura de buttercream.",
         [("Harina", 0.06), ("Azúcar", 0.05), ("Mantequilla", 0.04),
          ("Huevos", 1), ("Crema para batir", 0.03), ("Vainilla", 2)]),

        ("Galletas Decoradas x20", "Galletas", 12000, "🍪",
         "Veinte galletas de mantequilla decoradas con royal icing.",
         [("Harina", 0.5), ("Azúcar", 0.35), ("Mantequilla", 0.3),
          ("Huevos", 2), ("Colorante alimentario", 20), ("Cajas de presentación", 1)]),

        ("Milhoja Individual", "Postres", 4500, "🍰",
         "Milhoja de hojaldre con crema pastelera y azúcar glass.",
         [("Harina", 0.1), ("Mantequilla", 0.08), ("Crema para batir", 0.12),
          ("Azúcar", 0.05), ("Huevos", 1)]),

        ("Éclair de Chocolate", "Postres", 3800, "🍫",
         "Éclair relleno de crema y cubierto con glaseado de chocolate.",
         [("Harina", 0.07), ("Huevos", 1), ("Mantequilla", 0.03),
          ("Chocolate amargo", 0.04), ("Crema para batir", 0.06), ("Azúcar", 0.04)]),
    ]

    productos = {}
    for nombre, cat, precio, emoji, desc, bom in catalogo:
        producto, created = Producto.objects.get_or_create(
            categoria=cats[cat],
            nombre=nombre,
            defaults={
                "precio_base": f(precio),
                "descripcion": desc,
                "imagen": emoji,
            },
        )
        if created:
            for insumo_nombre, cantidad in bom:
                ComponenteProducto.objects.get_or_create(
                    producto=producto,
                    insumo=insumos[insumo_nombre],
                    defaults={"cantidad": f(cantidad)},
                )
        productos[nombre] = producto
    print(f"  ✓ {len(productos)} productos con BOM")

    # --- Clientes ---------------------------------------------------------
    datos_clientes = [
        ("Carla Muñoz", "carla.munoz@gmail.com", "+56981234567", "Av. Providencia 1234", "Providencia"),
        ("Roberto Pavez", "rpavez@outlook.com", "+56977654321", "Los Alerces 456", "La Florida"),
        ("Estefanía Ríos", "stef.rios@gmail.com", "+56965554433", "San Martín 789", "Ñuñoa"),
        ("Empresa Verde SpA", "contacto@empresaverde.cl", "+56955443322", "Av. Apoquindo 4500", "Las Condes"),
        ("Diego Salinas", "dsalinas@gmail.com", "+56944332211", "Calle Real 321", "Valparaíso"),
        ("Marcela Oyarzún", "marce.oy@gmail.com", "+56933221100", "El Poblado 89", "Maipú"),
    ]
    clientes = []
    for nombre, email, tel, dir_, comuna in datos_clientes:
        c, _ = Cliente.objects.get_or_create(
            nombre=nombre,
            defaults={"email": email, "telefono": tel, "direccion": dir_, "comuna": comuna},
        )
        clientes.append(c)
    print(f"  ✓ {len(clientes)} clientes")

    # --- Pedidos ----------------------------------------------------------
    ahora = timezone.now()
    estados = [
        Pedido.Estado.RECIBIDO,
        Pedido.Estado.EN_PREPARACION,
        Pedido.Estado.HORNEADO,
        Pedido.Estado.CONTROL,
        Pedido.Estado.LISTO,
    ]
    diseños = [
        "Torta de 2 pisos rosa con flores de azúcar y nombre 'Feliz Cumpleaños Sofía'",
        "Decoración minimalista blanco y dorado, topper de madera personalizado",
        "Tema dinosaurios: fondant verde, volcán de chocolate y figuras",
        "Caja surtida con logo de la empresa impreso en chocolate",
        "Corazón de frutas frescas y crema, base de bizcocho vainilla",
        "Set de cupcakes con colores corporativos y monograma",
    ]
    pedidos_creados = []
    for i, cliente in enumerate(clientes):
        n_items = 1 + (i % 3)
        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion_diseño=diseños[i % len(diseños)],
            ingredientes_especiales="Sin frutos secos" if i % 2 == 0 else "",
            fecha_entrega=ahora + timedelta(days=1 + i, hours=4 + i),
            prioridad=[Pedido.Prioridad.NORMAL, Pedido.Prioridad.ALTA, Pedido.Prioridad.URGENTE][i % 3],
            estado=estados[i % len(estados)],
            direccion_despacho=cliente.direccion,
            notas="Cliente habitual" if i % 2 == 0 else "",
            creador=admin_user,
        )
        # Detalles: se crea directo para evitar doble save
        elegidos = list(productos.values())
        for j in range(n_items):
            prod = elegidos[(i + j) % len(elegidos)]
            DetallePedido.objects.create(
                pedido=pedido,
                producto=prod,
                cantidad=1 + ((i + j) % 3),
                precio_unitario=prod.precio_base,
            )
        pedido.save()  # recalcula totales
        pedidos_creados.append(pedido)
    print(f"  ✓ {len(pedidos_creados)} pedidos en distintos estados")

    # --- Despachos --------------------------------------------------------
    for i, pedido in enumerate(pedidos_creados[:4]):
        Despacho.objects.get_or_create(
            pedido=pedido,
            defaults={
                "transportista": "Propio" if i % 2 == 0 else "Shipment Chile",
                "fecha_programada": pedido.fecha_entrega,
                "direccion": pedido.direccion_despacho or pedido.cliente.direccion,
                "estado": Despacho.Estado.PENDIENTE,
            },
        )
    print("  ✓ 4 despachos programados")

    # --- Un pedido atrasado de ejemplo ------------------------------------
    if not Pedido.objects.filter(descripcion_diseño__contains="URGENTE demo").exists():
        demo = Pedido.objects.create(
            cliente=clientes[0],
            descripcion_diseño="URGENTE demo: torta de emergencia para evento",
            fecha_entrega=ahora - timedelta(hours=6),
            prioridad=Pedido.Prioridad.URGENTE,
            estado=Pedido.Estado.EN_PREPARACION,
            creador=admin_user,
        )
        prod = productos["Torta de Chocolate 3 capas"]
        DetallePedido.objects.create(pedido=demo, producto=prod, cantidad=1,
                                      precio_unitario=prod.precio_base)
        demo.save()
        print("  ✓ 1 pedido atrasado (para demostrar alertas)")

    print("\n== Listo ==")
    print("  admin / admin1234   → Django Admin")
    print("  cocina / demo1234   → rol cocina")
    print("  python manage.py runserver")


if __name__ == "__main__":
    main()
