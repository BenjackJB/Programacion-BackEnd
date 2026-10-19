"""
Cliente del API REST de TRANSBANK WEBPAY PLUS (ambiente de integración).

Integración oficial descrita por Transbank (API REST Webpay Plus):
1. crear_transaccion()  POST /rswebpaytransaction/api/webpay/v1.2/transactions
   -> devuelve {token, url}: el navegador del usuario hace POST del campo
   `token_ws` a esa `url` para ver la página de pago de Webpay.
2. confirmar_transaccion()  PUT /rswebpaytransaction/api/webpay/v1.2/transactions/{token}
   -> devuelve el resultado del commit (status, response_code,
      authorization_code, etc.).

Autenticación por cabeceras `Tbk-Api-Key-Id` (código de comercio) y
`Tbk-Api-Key-Secret` (API key), ambos leídos de settings.WEBPAY.

Por defecto apunta al ambiente de INTEGRACIÓN (sandbox) de Transbank con las
credenciales públicas de prueba (sin cuenta real); se puede reconfigurar por
variables de entorno (WEBPAY_BASE_URL, WEBPAY_CODIGO_COMERCIO, WEBPAY_API_KEY)
sin tocar el código.
"""

import requests
from django.conf import settings


class ErrorWebpay(Exception):
    """Error de comunicación o de respuesta inesperada del API de Webpay."""


def _url_base():
    return settings.WEBPAY['BASE_URL'].rstrip('/')


def _cabeceras():
    """Cabeceras de autenticación exigidas por el API de Webpay."""
    return {
        'Tbk-Api-Key-Id': settings.WEBPAY['CODIGO_COMERCIO'],
        'Tbk-Api-Key-Secret': settings.WEBPAY['API_KEY'],
        'Content-Type': 'application/json',
    }


def _timeout():
    return settings.WEBPAY['TIMEOUT']


def crear_transaccion(buy_order, session_id, amount, return_url):
    """
    Crea la transacción en Webpay y devuelve (token, url_de_pago).

    - buy_order : orden de compra única por intento (máx. 26 caracteres).
    - session_id: identificador de sesión del checkout.
    - amount    : monto total en pesos (CLP, hasta 2 decimales).
    - return_url: URL de retorno del navegador (vista de retorno del sitio).
    """
    url = f'{_url_base()}/rswebpaytransaction/api/webpay/v1.2/transactions'
    cuerpo = {
        'buy_order': buy_order,
        'session_id': session_id,
        'amount': amount,
        'return_url': return_url,
    }
    try:
        respuesta = requests.post(url, json=cuerpo, headers=_cabeceras(), timeout=_timeout())
    except requests.RequestException as exc:
        raise ErrorWebpay(f'No fue posible contactar con Webpay: {exc}') from exc

    if respuesta.status_code != 200:
        raise ErrorWebpay(f'Webpay respondió HTTP {respuesta.status_code}: {respuesta.text[:300]}')

    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise ErrorWebpay('Webpay devolvió una respuesta que no es JSON.') from exc

    token = datos.get('token')
    destino = datos.get('url')
    if not token or not destino:
        raise ErrorWebpay('Webpay no devolvió el token ni la URL de pago.')
    return token, destino


def confirmar_transaccion(token):
    """
    Confirma (commit) la transacción y devuelve el dict de resultado.

    Campos útiles del resultado: `status` (AUTHORIZED / ...),
    `response_code` (0 = aprobada), `authorization_code`, `amount`.
    """
    url = f'{_url_base()}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}'
    try:
        respuesta = requests.put(url, json={}, headers=_cabeceras(), timeout=_timeout())
    except requests.RequestException as exc:
        raise ErrorWebpay(f'No fue posible confirmar el pago con Webpay: {exc}') from exc

    if respuesta.status_code != 200:
        raise ErrorWebpay(f'Webpay respondió HTTP {respuesta.status_code}: {respuesta.text[:300]}')

    try:
        return respuesta.json()
    except ValueError as exc:
        raise ErrorWebpay('Webpay devolvió una respuesta que no es JSON.') from exc
