"""Pruebas de SEGURIDAD: autenticación, autorización por rol, inyección SQL y fuga de datos."""
import httpx
import jwt
import pytest

from tests.conftest import AUTH, CATALOGO, PAGOS, PEDIDOS, auth

pytestmark = pytest.mark.security


@pytest.mark.caso("CP-22", "Endpoints protegidos rechazan peticiones sin token o con token manipulado")
def test_sin_token_y_token_falso(token_tecnico):
    protegidos = [("GET", f"{AUTH}/api/clientes/1"), ("GET", f"{CATALOGO}/api/onus/criticas"),
                  ("GET", f"{PEDIDOS}/api/tickets/pendientes"), ("GET", f"{PAGOS}/api/pagos/cierre-diario")]
    for metodo, url in protegidos:
        assert httpx.request(metodo, url).status_code == 401, url
    # Token firmado con otra clave y con rol elevado
    falso = jwt.encode({"sub": "1", "rol": "Administrador", "correo": "x@x.com"}, "clave-del-atacante-que-no-conoce-el-secreto-real", algorithm="HS256")
    assert httpx.get(f"{PAGOS}/api/pagos/cierre-diario", headers=auth(falso)).status_code == 401
    # Payload alterado manteniendo la firma original
    h, _, s = token_tecnico.split(".")
    alterado = h + "." + jwt.utils.base64url_encode(b'{"sub":"1","rol":"Administrador"}').decode() + "." + s
    assert httpx.get(f"{PAGOS}/api/pagos/cierre-diario", headers=auth(alterado)).status_code == 401


@pytest.mark.caso("CP-23", "Control de acceso por rol: el suscriptor no cobra ni ve datos de otros")
def test_autorizacion_por_rol(token_suscriptor):
    pago = httpx.post(f"{PAGOS}/api/pagos", headers=auth(token_suscriptor),
                      json={"id_factura": 2, "monto_pagado": 499, "metodo_pago": "Efectivo"})
    assert pago.status_code == 403
    assert httpx.get(f"{AUTH}/api/clientes/2", headers=auth(token_suscriptor)).status_code == 403
    assert httpx.get(f"{PAGOS}/api/facturas?id_cliente=2", headers=auth(token_suscriptor)).status_code == 403
    propio = httpx.get(f"{AUTH}/api/clientes/1", headers=auth(token_suscriptor))
    assert propio.status_code == 200 and "password_hash" not in propio.json()


@pytest.mark.caso("CP-24", "Intentos de inyección SQL no evaden la autenticación ni exponen errores")
@pytest.mark.parametrize("payload", ["' OR '1'='1", "admin'--", "x'; DROP TABLE usuarios_db.clientes; --"])
def test_inyeccion_sql(payload, token_tecnico):
    r = httpx.post(f"{AUTH}/api/auth/login", json={"correo": payload, "password": payload})
    assert r.status_code == 401
    assert "syntax" not in r.text.lower() and "traceback" not in r.text.lower()
    f = httpx.get(f"{PAGOS}/api/facturas", params={"id_cliente": 1, "estado": payload}, headers=auth(token_tecnico))
    assert f.status_code == 200 and f.json() == []
    # La tabla sigue existiendo
    assert httpx.post(f"{AUTH}/api/auth/login", json={"correo": "tecnico.campo@fivercable.com",
                                                       "password": "Tecnico2026!"}).status_code == 200
