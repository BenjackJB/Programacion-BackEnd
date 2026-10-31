#!/usr/bin/env bash
# ============================================================================
# Dulce Arte — configuración completa del servidor Ubuntu (AWS EC2)
#
# Uso (una sola vez, el domingo en la noche):
#   chmod +x deploy/configurar_servidor.sh
#   sudo ./deploy/configurar_servidor.sh
#
# Qué hace:
#   1. Instala Python, virtualenv, Nginx, Git y PostgreSQL
#   2. Crea el entorno virtual e instala las dependencias
#   3. Crea la base de datos PostgreSQL y su usuario
#   4. Genera el archivo .env con valores seguros
#   5. Aplica migraciones y crea datos demo
#   6. Recopila estáticos
#   7. Configura e inicia Gunicorn (systemd) y Nginx
# ============================================================================
set -euo pipefail

APP_DIR="/home/ubuntu/apps"
VENV_DIR="$APP_DIR/venv"
DB_NAME="dulce_arte"
DB_USER="dulce"
DB_PASS="dulce_2026"

echo "=============================================="
echo " Dulce Arte · configuración del servidor"
echo "=============================================="

# ---------------------------------------------------------------------------
# 1. Paquetes del sistema
# ---------------------------------------------------------------------------
echo ">> [1/8] Instalando paquetes del sistema..."
sudo apt-get update -y
sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    build-essential libpq-dev \
    nginx git \
    postgresql postgresql-contrib

# ---------------------------------------------------------------------------
# 2. Directorio del proyecto y entorno virtual
# ---------------------------------------------------------------------------
echo ">> [2/8] Preparando directorio y entorno virtual..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Si el proyecto no está clonado, se asume que ya fue copiado por git.
if [ ! -f "$APP_DIR/manage.py" ]; then
    echo "   ⚠ No se encontró manage.py en $APP_DIR."
    echo "   Clona el repositorio primero:"
    echo "     cd $APP_DIR && git clone <URL_DEL_REPO> . "
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# 3. Base de datos PostgreSQL
# ---------------------------------------------------------------------------
echo ">> [3/8] Configurando PostgreSQL..."
sudo -u postgres psql <<PSQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='$DB_USER') THEN
      CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';
   END IF;
END
\$\$;
PSQL

# Crear la base de datos si no existe
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
if [ "$DB_EXISTS" != "1" ]; then
    sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"
fi
echo "   ✓ Base de datos '$DB_NAME' y usuario '$DB_USER' listos."

# ---------------------------------------------------------------------------
# 4. Archivo .env de producción
# ---------------------------------------------------------------------------
echo ">> [4/8] Generando .env de producción..."
if [ ! -f "$APP_DIR/.env" ]; then
    SECRET=$(python -c "from django.core.management.utils import get_random_secret_key as g; print(g())")
    cat > "$APP_DIR/.env" <<ENV
SECRET_KEY=$SECRET
DEBUG=0
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
ENV
    echo "   ✓ .env creado. EDITA ALLOWED_HOSTS con la IP elástica (ver paso final)."
else
    echo "   • .env ya existe, se conserva."
fi

# ---------------------------------------------------------------------------
# 5. Migraciones + datos demo
# ---------------------------------------------------------------------------
echo ">> [5/8] Aplicando migraciones..."
cd "$APP_DIR"
python manage.py migrate --noinput

if [ -f "$APP_DIR/setup_demo.py" ]; then
    echo ">> Sembrando datos demo (opcional)..."
    python setup_demo.py || echo "   ⚠ setup_demo.py falló (¿ya hay datos?), continúa."
fi

# ---------------------------------------------------------------------------
# 6. Archivos estáticos
# ---------------------------------------------------------------------------
echo ">> [6/8] Recopilando estáticos (collectstatic)..."
python manage.py collectstatic --noinput

# ---------------------------------------------------------------------------
# 7. Permisos para que Nginx (www-data) alcance el socket
# ---------------------------------------------------------------------------
echo ">> [7/8] Ajustando permisos (grupos www-data/ubuntu)..."
sudo usermod -aG www-data ubuntu || true
sudo usermod -aG ubuntu www-data  || true
sudo chmod 750 /home/ubuntu
sudo chmod 770 "$APP_DIR"

# ---------------------------------------------------------------------------
# 8. Gunicorn + Nginx
# ---------------------------------------------------------------------------
echo ">> [8/8] Configurando Gunicorn y Nginx..."

# Servicio systemd de Gunicorn
sudo cp "$APP_DIR/deploy/gunicorn.service" /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn

# Sitio de Nginx
sudo cp "$APP_DIR/deploy/nginx_dulce_arte" /etc/nginx/sites-available/dulce_arte
sudo ln -sf /etc/nginx/sites-available/dulce_arte /etc/nginx/sites-enabled/
# Quitar el sitio default para evitar conflictos
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Permisos del socket (Gunicorn lo crea como ubuntu:www-data)
sleep 2
if [ -S "$APP_DIR/dulce_arte.sock" ]; then
    sudo chown ubuntu:www-data "$APP_DIR/dulce_arte.sock"
    sudo chmod 660 "$APP_DIR/dulce_arte.sock"
fi

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
echo ""
echo "=============================================="
echo " ✅ Servidor configurado"
echo "=============================================="
echo " Estado de los servicios:"
sudo systemctl is-active gunicorn && echo "   gunicorn: activo"
sudo systemctl is-active nginx    && echo "   nginx:    activo"
echo ""
echo " Prueba local dentro de la instancia:"
echo "   curl -I http://localhost/"
echo ""
echo " ⚠ SIGUIENTE PASO IMPORTANTE:"
echo "   1. Asocia la IP elástica (Elastic IP) a esta instancia."
echo "   2. Edita el .env y agrega la IP en ALLOWED_HOSTS y PUBLIC_HOST:"
echo "        sudo nano $APP_DIR/.env"
echo "      ALLOWED_HOSTS=localhost,127.0.0.1,<TU_IP_ELASTICA>"
echo "      PUBLIC_HOST=<TU_IP_ELASTICA>"
echo "   3. Reinicia los servicios:"
echo "        sudo systemctl restart gunicorn && sudo systemctl restart nginx"
echo "   4. Abre:  http://<TU_IP_ELASTICA>/"
echo "=============================================="
