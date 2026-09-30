"""Pruebas de ACEPTACIÓN automatizadas con Selenium sobre el portal de cobro en campo."""
import os
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.conftest import PAGOS, SUSCRIPTOR, TECNICO

pytestmark = pytest.mark.acceptance
CAPTURAS = Path(os.getenv("REPORTS_DIR", "reports")) / "capturas"


@pytest.fixture
def navegador():
    opts = Options()
    if os.getenv("HEADLESS", "1") == "1":
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=420,900")   # tamaño de teléfono del técnico
    if os.getenv("CHROME_BIN"):
        opts.binary_location = os.environ["CHROME_BIN"]
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(2)
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    yield d
    d.quit()


def ingresar(d, correo, password):
    d.get(f"{PAGOS}/portal")
    d.find_element(By.ID, "correo").send_keys(correo)
    d.find_element(By.ID, "password").send_keys(password)
    d.find_element(By.ID, "btn-login").click()


@pytest.mark.caso("CP-20", "Aceptación: el técnico cobra una factura desde el portal móvil")
def test_tecnico_cobra_factura(navegador, factura_pendiente):
    d = navegador
    ingresar(d, *TECNICO)
    WebDriverWait(d, 10).until(EC.visibility_of_element_located((By.ID, "seccion-cobro")))
    d.find_element(By.ID, "id-cliente").send_keys("1")
    Select(d.find_element(By.ID, "metodo")).select_by_value("Efectivo")
    d.find_element(By.ID, "btn-buscar").click()
    fila_id = f"factura-{factura_pendiente['id_factura']}"
    fila = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, fila_id)))
    d.save_screenshot(str(CAPTURAS / "CP-20_facturas_pendientes.png"))
    fila.find_element(By.CSS_SELECTOR, "button.cobrar").click()
    WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, "id-transaccion")))
    assert d.find_element(By.ID, fila_id).find_element(By.CLASS_NAME, "estado").text == "Pagado"
    assert d.find_element(By.ID, "id-transaccion").text.startswith("FC-")
    d.save_screenshot(str(CAPTURAS / "CP-20_pago_registrado.png"))


@pytest.mark.caso("CP-21", "Aceptación: un suscriptor no puede operar el portal de cobro")
def test_suscriptor_rechazado(navegador):
    d = navegador
    ingresar(d, *SUSCRIPTOR)
    msg = WebDriverWait(d, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#login-msg .msg")))
    assert "Solo personal técnico" in msg.text
    assert not d.find_element(By.ID, "seccion-cobro").is_displayed()
    d.save_screenshot(str(CAPTURAS / "CP-21_suscriptor_rechazado.png"))
