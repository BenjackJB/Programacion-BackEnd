#!/usr/bin/env bash
# ============================================================================
# Dulce Arte — actualización rápida del despliegue
# Úsalo cuando hagas `git pull` con cambios nuevos.
#
#   chmod +x deploy/actualizar.sh
#   ./deploy/actualizar.sh
# ============================================================================
set -euo pipefail

APP_DIR="/home/ubuntu/apps"
cd "$APP_DIR"

echo ">> Activando entorno virtual..."
source "$APP_DIR/venv/bin/activate"

echo ">> Instalando dependencias (por si cambiaron)..."
pip install -r requirements.txt

echo ">> Migraciones..."
python manage.py migrate --noinput

echo ">> Collectstatic..."
python manage.py collectstatic --noinput

echo ">> Reiniciando Gunicorn..."
sudo systemctl restart gunicorn

echo ">> Reiniciando Nginx..."
sudo systemctl restart nginx

# Reasegurar permisos del socket
sleep 2
if [ -S "$APP_DIR/dulce_arte.sock" ]; then
    sudo chown ubuntu:www-data "$APP_DIR/dulce_arte.sock"
    sudo chmod 660 "$APP_DIR/dulce_arte.sock"
fi

echo ""
echo "✅ Despliegue actualizado. Estado:"
sudo systemctl is-active gunicorn
sudo systemctl is-active nginx
