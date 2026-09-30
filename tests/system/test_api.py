"""Pruebas de SISTEMA: API REST de los cuatro microservicios desplegados (contenedores)."""
import time

import httpx
import pytest

from tests.conftest import AUTH, CATALOGO, PAGOS, PEDIDOS, TECNICO, auth

pytestmark = pytest.mark.system


@pytest.mark.caso("CP-14", "Endpoint /health de los 4 microservicios con conexión a BD")
@pytest.mark.parametrize("url,esquema", [
    (AUTH, "usuarios_db"), (CATALOGO, "red_db"), (PEDIDOS, "soporte_db"), (PAGOS, "billing_db"),
])
def test_health(url, esquema):
    r = httpx.get(f"{url}/health", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "OK" and body["db"] is True and body["esquema"] == esquema


@pytest.mark.caso("CP-15", "Login del técnico emite JWT; credenciales inválidas devuelven 401")
def test_login():
    ok = httpx.post(f"{AUTH}/api/auth/login", json={"correo": TECNICO[0], "password": TECNICO[1]})
    assert ok.status_code == 200 and ok.json()["rol"] == "Tecnico"
    assert ok.json()["access_token"].count(".") == 2
    mal = httpx.post(f"{AUTH}/api/auth/login", json={"correo": TECNICO[0], "password": "incorrecta"})
    assert mal.status_code == 401


@pytest.mark.caso("CP-16", "Cobro en campo: el técnico registra el pago y la factura queda Pagado")
def test_flujo_cobro(token_tecnico, factura_pendiente):
    r = httpx.post(f"{PAGOS}/api/pagos", headers=auth(token_tecnico), json={
        "id_factura": factura_pendiente["id_factura"], "monto_pagado": 299.00, "metodo_pago": "Efectivo"})
    assert r.status_code == 201, r.text
    assert r.json()["estado_factura"] == "Pagado"
    assert r.json()["id_transaccion_pasarela"].startswith("FC-")


@pytest.mark.caso("CP-17", "No se permite cobrar dos veces la misma factura ni montos distintos")
def test_cobro_duplicado_y_monto(token_tecnico, factura_pendiente):
    base = {"id_factura": factura_pendiente["id_factura"], "metodo_pago": "Efectivo"}
    parcial = httpx.post(f"{PAGOS}/api/pagos", headers=auth(token_tecnico), json={**base, "monto_pagado": 100})
    assert parcial.status_code == 422
    assert httpx.post(f"{PAGOS}/api/pagos", headers=auth(token_tecnico), json={**base, "monto_pagado": 299}).status_code == 201
    dup = httpx.post(f"{PAGOS}/api/pagos", headers=auth(token_tecnico), json={**base, "monto_pagado": 299})
    assert dup.status_code == 409


@pytest.mark.caso("CP-18", "Registro de ONU por API: MAC válida 201, MAC duplicada 409")
def test_registro_onu(token_tecnico):
    sufijo = f"{int(time.time()*1000) % 0xFFFFFF:06X}"
    mac = f"AA:BB:CC:{sufijo[0:2]}:{sufijo[2:4]}:{sufijo[4:6]}"
    datos = {"id_cliente_ref": 1, "mac_address": mac.replace(":", "-").lower(), "serial_number": "HWTC55555555",
             "puerto_olt": "Slot2/Pon4", "potencia_optica_dbm": -21.3}
    r = httpx.post(f"{CATALOGO}/api/onus", headers=auth(token_tecnico), json=datos)
    assert r.status_code == 201, r.text
    assert r.json()["mac_address"] == mac and r.json()["clasificacion_senal"] == "Normal"
    assert httpx.post(f"{CATALOGO}/api/onus", headers=auth(token_tecnico), json=datos).status_code == 409


@pytest.mark.caso("CP-19", "Creación de ticket con prioridad automática y cierre por el técnico")
def test_ticket(token_tecnico):
    r = httpx.post(f"{PEDIDOS}/api/tickets", headers=auth(token_tecnico), json={
        "id_cliente_ref": 1, "tipo_incidencia": "Falla", "descripcion_falla": "Cliente sin internet, fibra cortada"})
    assert r.status_code == 201
    t = r.json()
    assert t["prioridad"] == "Critica" and t["sla_horas"] == 4
    c = httpx.post(f"{PEDIDOS}/api/tickets/{t['id_ticket']}/cerrar", headers=auth(token_tecnico))
    assert c.status_code == 200 and c.json()["estado_ticket"] == "Cerrado"
