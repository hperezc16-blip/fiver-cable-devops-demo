"""Pruebas de aceptación con Selenium sobre el prototipo de Fiver Cable (prototipo/index.html).

Recorren el prototipo como lo haría cada tipo de usuario: cliente, técnico y administrador.
Se pueden ejecutar en el pipeline (sin ventana) o en una computadora con el navegador visible:

    set HEADLESS=0
    set PAUSA=1
    python -m pytest tests/acceptance
"""
import os
import time
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

pytestmark = pytest.mark.acceptance

RAIZ = Path(__file__).resolve().parents[2]
PROTOTIPO = os.getenv("PROTOTIPO_URL", (RAIZ / "prototipo" / "index.html").as_uri())
CAPTURAS = Path(os.getenv("REPORTS_DIR", "reports")) / "capturas"
PAUSA = float(os.getenv("PAUSA", "0"))


@pytest.fixture
def navegador():
    opciones = Options()
    if os.getenv("HEADLESS", "1") == "1":
        opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=430,900")
    if os.getenv("CHROME_BIN"):
        opciones.binary_location = os.environ["CHROME_BIN"]
    driver = webdriver.Chrome(options=opciones)
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    driver.get(PROTOTIPO)
    yield driver
    driver.quit()


def esperar(driver, segundos=PAUSA):
    if segundos:
        time.sleep(segundos)


def boton(driver, texto, indice=0):
    xpath = f"//button[contains(normalize-space(.), '{texto}')]"

    def visibles(d):
        encontrados = [b for b in d.find_elements(By.XPATH, xpath) if b.is_displayed()]
        return encontrados if len(encontrados) > indice else False

    WebDriverWait(driver, 10).until(visibles)[indice].click()
    esperar(driver)


def pantalla(driver):
    return driver.find_element(By.ID, "view").text


def ingresar(driver, perfil):
    boton(driver, perfil)
    boton(driver, "Ingresar")


def captura(driver, nombre):
    driver.save_screenshot(str(CAPTURAS / f"{nombre}.png"))


@pytest.mark.caso("CP-29", "El cliente paga su factura pendiente desde el prototipo")
def test_cliente_paga_factura(navegador):
    d = navegador
    ingresar(d, "Cliente")
    assert "Hola, María" in pantalla(d)
    boton(d, "Facturas")
    assert "Pendiente" in pantalla(d)
    captura(d, "CP-29_1_facturas_pendientes")
    boton(d, "Ver detalle")
    boton(d, "Pagar ahora")
    boton(d, "Continuar")
    assert "Revisa tu pago" in pantalla(d)
    boton(d, "Confirmar pago")
    assert "Pago registrado" in pantalla(d)
    captura(d, "CP-29_2_pago_registrado")
    boton(d, "Ver mis facturas")
    assert "Pendiente" not in pantalla(d)
    captura(d, "CP-29_3_facturas_pagadas")


@pytest.mark.caso("CP-30", "El técnico registra el cobro en campo y se genera el recibo digital")
def test_tecnico_registra_cobro(navegador):
    d = navegador
    ingresar(d, "Técnico")
    assert "Visitas asignadas" in pantalla(d)
    captura(d, "CP-30_1_rutas_del_dia")
    boton(d, "Iniciar visita", 2)
    assert "Ana García" in pantalla(d)
    boton(d, "Registrar cobro")
    monto = d.find_element(By.ID, "amount")
    monto.clear()
    monto.send_keys("0")
    boton(d, "Confirmar cobro")
    assert "Registrar pago" in pantalla(d)
    assert d.execute_script("return arguments[0].validity.valid", monto) is False
    monto.clear()
    monto.send_keys("325")
    Select(d.find_element(By.ID, "collectMethod")).select_by_visible_text("Efectivo")
    captura(d, "CP-30_2_registro_de_cobro")
    boton(d, "Confirmar cobro")
    texto = pantalla(d)
    assert "Cobro registrado" in texto
    assert "Ana García" in texto and "Q 325.00" in texto
    captura(d, "CP-30_3_recibo_digital")


@pytest.mark.caso("CP-31", "El cliente reporta una falla y recibe su número de ticket")
def test_cliente_reporta_falla(navegador):
    d = navegador
    ingresar(d, "Cliente")
    boton(d, "Soporte")
    Select(d.find_element(By.ID, "issue")).select_by_visible_text("Sin señal")
    d.find_element(By.ID, "description").send_keys("No tengo internet desde esta mañana en zona 11.")
    captura(d, "CP-31_1_reporte_de_falla")
    boton(d, "Enviar reporte")
    texto = pantalla(d)
    assert "Reporte recibido" in texto
    assert "Abierto" in texto
    captura(d, "CP-31_2_ticket_generado")


@pytest.mark.caso("CP-32", "El administrador registra un equipo y no se permite repetir la serie (RN-02)")
def test_admin_registra_equipo_unico(navegador):
    d = navegador
    ingresar(d, "Administrador")
    assert "Panel administrativo" in pantalla(d)
    boton(d, "Inventario")
    boton(d, "Registrar")
    d.find_element(By.ID, "equipmentSerial").send_keys("FIV-MOD-900")
    boton(d, "Guardar equipo")
    assert "FIV-MOD-900" in pantalla(d)
    captura(d, "CP-32_1_equipo_registrado")
    boton(d, "Inventario")
    boton(d, "Registrar")
    d.find_element(By.ID, "equipmentSerial").send_keys("FIV-MOD-900")
    boton(d, "Guardar equipo")
    aviso = WebDriverWait(d, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#toast .toast")))
    assert "serie único" in aviso.text
    captura(d, "CP-32_2_serie_repetida_rechazada")


@pytest.mark.caso("CP-33", "Jefatura consulta indicadores y supervisa la operación")
def test_jefatura_consulta_dashboard(navegador):
    d = navegador
    ingresar(d, "Jefatura")
    texto = pantalla(d)
    assert "Panel de jefatura" in texto
    assert "CLIENTES ACTIVOS" in texto
    assert "VISITAS REGISTRADAS" in texto
    assert "Indicadores ilustrativos" in texto
    captura(d, "CP-33_dashboard_jefatura")
    boton(d, "Ver ingresos y egresos")
    assert "Ingresos y egresos" in pantalla(d)


@pytest.mark.caso("CP-34", "Secretaría agenda una visita para cliente y técnico")
def test_secretaria_agenda_visita(navegador):
    d = navegador
    ingresar(d, "Secretaría")
    assert "Atención de oficina" in pantalla(d)
    boton(d, "Agendar visita técnica")
    boton(d, "Programar visita")
    Select(d.find_element(By.ID, "visitClient")).select_by_visible_text("Carlos Méndez")
    Select(d.find_element(By.ID, "visitTechnician")).select_by_visible_text("Luis Herrera")
    d.execute_script("arguments[0].value = '2026-10-10'", d.find_element(By.ID, "visitDate"))
    d.find_element(By.ID, "visitNote").send_keys("Revisar conexión y confirmar señal.")
    boton(d, "Guardar en agenda demo")
    texto = pantalla(d)
    assert "Visitas programadas · 5" in texto
    assert "2026-10-10 · Luis Herrera" in texto
    captura(d, "CP-34_agenda_secretaria")


@pytest.mark.caso("CP-35", "Secretaría registra un pago de oficina con autorización")
def test_secretaria_registra_pago_oficina(navegador):
    d = navegador
    ingresar(d, "Secretaría")
    boton(d, "Registrar pago de oficina")
    Select(d.find_element(By.ID, "officeMethod")).select_by_visible_text("Tarjeta")
    boton(d, "Confirmar pago simulado")
    aviso = WebDriverWait(d, 5).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "#toast .toast"))
    )
    assert "autorización" in aviso.text
    d.find_element(By.ID, "officeAuthorization").send_keys("AUTH-DEMO-2046")
    boton(d, "Confirmar pago simulado")
    texto = pantalla(d)
    assert "Pago de oficina registrado" in texto
    assert "Patricia Gómez" in texto
    assert "Q 325.00" in texto
    assert "no se movió dinero" in texto
    captura(d, "CP-35_recibo_pago_oficina")


@pytest.mark.caso("CP-39", "Administración puede cambiar el estado demo de una cuenta")
def test_admin_cambia_estado_cuenta_demo(navegador):
    d = navegador
    ingresar(d, "Administrador")
    boton(d, "Usuarios")
    d.find_element(By.ID, "userList").find_element(
        By.XPATH, ".//div[contains(@class, 'card')]"
    ).click()
    Select(d.find_element(By.ID, "demoUserState")).select_by_visible_text("Suspendido")
    boton(d, "Aplicar estado (demo)")
    assert "Suspendido" in pantalla(d)
    assert "solo en la demostración" in d.find_element(By.ID, "toast").text
    captura(d, "CP-39_estado_suspendido_demo")
    d.find_element(By.CSS_SELECTOR, "button.back").click()
    boton(d, "Inicio")
    assert "SUSPENDIDOS" in pantalla(d)
    assert "2" in pantalla(d)
