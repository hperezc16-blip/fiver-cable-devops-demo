"""Pruebas de SEGURIDAD de los roles de oficina (Jefatura, Secretaría) y del aislamiento del suscriptor."""
import os

import httpx
import pytest

from tests.conftest import AUTH, CATALOGO, PAGOS, PEDIDOS, _login, auth

pytestmark = pytest.mark.security

JEFATURA = (os.getenv("TEST_JEFATURA_EMAIL", "jefatura@fivercable.com"),
            os.getenv("TEST_JEFATURA_PASSWORD", "Jefatura2026!"))
SECRETARIA = (os.getenv("TEST_SECRETARIA_EMAIL", "secretaria@fivercable.com"),
              os.getenv("TEST_SECRETARIA_PASSWORD", "Secretaria2026!"))


@pytest.fixture(scope="module")
def token_jefatura() -> str:
    return _login(*JEFATURA)


@pytest.fixture(scope="module")
def token_secretaria() -> str:
    return _login(*SECRETARIA)


@pytest.mark.caso("CP-40", "Jefatura consulta indicadores y auditoría, pero no cobra ni modifica datos")
def test_jefatura_solo_lectura(token_jefatura, factura_pendiente):
    h = auth(token_jefatura)
    assert httpx.get(f"{PAGOS}/api/resumen", headers=h).status_code == 200
    assert httpx.get(f"{AUTH}/api/auditoria", headers=h).status_code == 200
    assert httpx.get(f"{PAGOS}/api/pagos/cierre-diario", headers=h).status_code == 200
    pago = httpx.post(f"{PAGOS}/api/pagos", headers=h, json={
        "id_factura": factura_pendiente["id_factura"], "monto_pagado": 299, "metodo_pago": "Efectivo"})
    assert pago.status_code == 403
    assert httpx.patch(f"{AUTH}/api/clientes/2/estado", headers=h,
                       json={"estado_servicio": "Moroso"}).status_code == 403
    assert httpx.post(f"{PAGOS}/api/facturas", headers=h,
                      json={"id_cliente_ref": 1, "monto_total": 100}).status_code == 403


@pytest.mark.caso("CP-41", "Secretaría emite factura y cobra en oficina, pero no opera la red")
def test_secretaria_oficina(token_secretaria):
    h = auth(token_secretaria)
    factura = httpx.post(f"{PAGOS}/api/facturas", headers=h, json={"id_cliente_ref": 1, "monto_total": 199})
    assert factura.status_code == 201, factura.text
    sin_aut = httpx.post(f"{PAGOS}/api/pagos", headers=h, json={
        "id_factura": factura.json()["id_factura"], "monto_pagado": 199, "metodo_pago": "Tarjeta"})
    assert sin_aut.status_code == 422
    pago = httpx.post(f"{PAGOS}/api/pagos", headers=h, json={
        "id_factura": factura.json()["id_factura"], "monto_pagado": 199, "metodo_pago": "Tarjeta",
        "codigo_autorizacion": "AUT-TEST-01"})
    assert pago.status_code == 201 and pago.json()["registrado_por"] == SECRETARIA[0]
    assert httpx.post(f"{CATALOGO}/api/onus/estado", headers=h,
                      json={"id_cliente": 1, "nuevo_estado": "Online"}).status_code == 403
    assert httpx.get(f"{AUTH}/api/auditoria", headers=h).status_code == 403


@pytest.mark.caso("CP-42", "El suscriptor solo ve sus propios tickets y equipos y no lista clientes ni pagos")
def test_suscriptor_aislado(token_suscriptor):
    h = auth(token_suscriptor)
    assert httpx.get(f"{AUTH}/api/clientes", headers=h).status_code == 403
    assert httpx.get(f"{PAGOS}/api/pagos", headers=h).status_code == 403
    assert httpx.get(f"{PAGOS}/api/resumen", headers=h).status_code == 403
    for url in (f"{PEDIDOS}/api/tickets?id_cliente=2", f"{CATALOGO}/api/onus?id_cliente=2"):
        r = httpx.get(url, headers=h)
        assert r.status_code == 200 and all(f["id_cliente_ref"] == 1 for f in r.json()), url
    facturas = httpx.get(f"{PAGOS}/api/facturas", headers=h)
    assert facturas.status_code == 200 and all(f["id_cliente_ref"] == 1 for f in facturas.json())


@pytest.mark.caso("CP-43", "La auditoría registra al usuario de la aplicación que cambió el estado")
def test_auditoria_usuario_aplicacion(token_tecnico, db_commit):
    h = auth(token_tecnico)
    actual = db_commit.execute("SELECT estado_servicio FROM usuarios_db.clientes WHERE id_cliente = 8").fetchone()
    destino = "Moroso" if actual["estado_servicio"] == "Activo" else "Activo"
    r = httpx.patch(f"{AUTH}/api/clientes/8/estado", headers=h, json={"estado_servicio": destino})
    assert r.status_code == 200, r.text
    fila = db_commit.execute("""SELECT usuario_operador FROM usuarios_db.auditoria_usuarios
                                WHERE id_cliente = 8 ORDER BY id_auditoria DESC LIMIT 1""").fetchone()
    assert fila["usuario_operador"] == "tecnico.campo@fivercable.com"
