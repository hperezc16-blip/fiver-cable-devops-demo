"""Captura evidencias del portal web (ms_pagos /portal) contra el entorno en ejecución.

Requiere los contenedores arriba con datos semilla recién cargados:
    docker compose down -v && docker compose up -d --build --wait
    python docs/evidencias/capturar_evidencias.py

Las contraseñas se leen de las variables TEST_* (o sus valores de demostración) y
nunca quedan visibles: los campos de contraseña del portal son de tipo password.
"""
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

PAGOS = os.getenv("PAGOS_URL", "http://localhost:3003")
CUENTAS = {
    "tecnico": (os.getenv("TEST_TECNICO_EMAIL", "tecnico.campo@fivercable.com"), os.getenv("TEST_TECNICO_PASSWORD", "Tecnico2026!")),
    "suscriptor": (os.getenv("TEST_SUSCRIPTOR_EMAIL", "hazel.perez@fivercable.com"), os.getenv("TEST_SUSCRIPTOR_PASSWORD", "Suscriptor2026!")),
    "admin": (os.getenv("TEST_ADMIN_EMAIL", "admin@fivercable.com"), os.getenv("TEST_ADMIN_PASSWORD", "Admin2026!")),
    "jefatura": (os.getenv("TEST_JEFATURA_EMAIL", "jefatura@fivercable.com"), os.getenv("TEST_JEFATURA_PASSWORD", "Jefatura2026!")),
    "secretaria": (os.getenv("TEST_SECRETARIA_EMAIL", "secretaria@fivercable.com"), os.getenv("TEST_SECRETARIA_PASSWORD", "Secretaria2026!")),
}
SALIDA = Path(__file__).parent / "capturas"


def navegador(ancho: int = 1280, alto: int = 900) -> webdriver.Chrome:
    opciones = webdriver.ChromeOptions()
    if os.getenv("HEADLESS", "1") == "1":
        opciones.add_argument("--headless=new")
    opciones.add_argument(f"--window-size={ancho},{alto}")
    return webdriver.Chrome(options=opciones)


def captura(d, nombre: str) -> None:
    time.sleep(0.6)
    d.save_screenshot(str(SALIDA / f"{nombre}.png"))
    print("captura", nombre)


def login(d, cuenta: str) -> None:
    correo, clave = CUENTAS[cuenta]
    d.get(f"{PAGOS}/portal")
    d.find_element(By.ID, "correo").send_keys(correo)
    d.find_element(By.ID, "password").send_keys(clave)
    d.find_element(By.ID, "btn-login").click()
    WebDriverWait(d, 10).until(EC.visibility_of_element_located((By.ID, "app")))
    esperar_vista(d)


def esperar_vista(d) -> None:
    WebDriverWait(d, 10).until(lambda x: "Cargando" not in x.find_element(By.ID, "vista").text)
    time.sleep(0.4)


def menu(d, vista: str) -> None:
    d.find_element(By.ID, f"nav-{vista}").click()
    esperar_vista(d)


def buscar(d, id_cliente: int, metodo: str = "Efectivo") -> None:
    campo = d.find_element(By.ID, "id-cliente")
    campo.clear()
    campo.send_keys(str(id_cliente))
    Select(d.find_element(By.ID, "metodo")).select_by_value(metodo)
    d.find_element(By.ID, "btn-buscar").click()


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    d = navegador()
    espera = WebDriverWait(d, 10)
    try:
        # Disponibilidad y API
        for nombre, puerto in (("auth", 3000), ("catalogo", 3001), ("pedidos", 3002), ("pagos", 3003)):
            d.get(f"{PAGOS.rsplit(':', 1)[0]}:{puerto}/health")
            captura(d, f"E01_health_ms_{nombre}")
        d.get(f"{PAGOS}/docs")
        espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".opblock")))
        captura(d, "E02_openapi_ms_pagos")
        d.get(f"{PAGOS}/api/facturas?id_cliente=1")
        captura(d, "S01_api_sin_token_401")

        # Inicio de sesión
        d.get(f"{PAGOS}/portal")
        espera.until(EC.visibility_of_element_located((By.ID, "correo")))
        captura(d, "M01_inicio_sesion")
        d.find_element(By.ID, "correo").send_keys(CUENTAS["tecnico"][0])
        d.find_element(By.ID, "password").send_keys("ClaveIncorrecta1")
        d.find_element(By.ID, "btn-login").click()
        espera.until(EC.text_to_be_present_in_element((By.ID, "login-msg"), "Credenciales"))
        captura(d, "S02_login_credenciales_invalidas")

        # Técnico: panel, cobro, rechazo, recibo y reactivación
        login(d, "tecnico")
        captura(d, "M02_panel_tecnico")
        menu(d, "cobro")
        buscar(d, 2, "Tarjeta")
        espera.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.cobrar")))
        captura(d, "M03_facturas_pendientes")
        d.find_element(By.CSS_SELECTOR, "button.cobrar").click()
        espera.until(EC.text_to_be_present_in_element((By.ID, "cobro-msg"), "autorización"))
        captura(d, "S03_cobro_rechazado_sin_autorizacion")
        Select(d.find_element(By.ID, "metodo")).select_by_value("Efectivo")
        d.find_element(By.CSS_SELECTOR, "button.cobrar").click()
        espera.until(EC.presence_of_element_located((By.ID, "id-transaccion")))
        captura(d, "M04_cobro_exitoso_recibo")
        buscar(d, 7)
        espera.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.cobrar")))
        for _ in range(2):
            d.find_element(By.CSS_SELECTOR, "button.cobrar").click()
            espera.until(EC.presence_of_element_located((By.ID, "id-transaccion")))
            time.sleep(0.6)
        espera.until(EC.element_to_be_clickable((By.ID, "btn-reactivar"))).click()
        espera.until(EC.text_to_be_present_in_element((By.ID, "toast"), "reactivado"))
        captura(d, "M05_reactivacion_servicio")
        menu(d, "tickets")
        captura(d, "M06_tickets_tecnico")
        menu(d, "perfil")
        captura(d, "M07_perfil_cambio_password")

        # Administrador: clientes, cierre, red, auditoría
        login(d, "admin")
        captura(d, "M08_panel_administrador")
        menu(d, "clientes")
        d.execute_script("detalleCliente(7)")
        time.sleep(1.2)
        captura(d, "M09_detalle_cliente")
        menu(d, "cierre")
        captura(d, "M10_cierre_diario")
        menu(d, "red")
        captura(d, "M11_red_equipos")
        menu(d, "auditoria")
        captura(d, "S05_auditoria_usuario_aplicacion")

        # Jefatura y Secretaría
        login(d, "jefatura")
        captura(d, "M12_panel_jefatura")
        login(d, "secretaria")
        menu(d, "facturacion")
        captura(d, "M13_facturacion_secretaria")

        # Cliente: su cuenta, sin opciones de cobro (autorización por rol)
        login(d, "suscriptor")
        captura(d, "S04_cliente_solo_su_cuenta")
    finally:
        d.quit()

    # Vista en celular
    m = navegador(400, 860)
    try:
        login(m, "suscriptor")
        captura(m, "M14_cliente_celular")
        m.find_element(By.ID, "menu-btn").click()
        captura(m, "M15_menu_celular")
    finally:
        m.quit()


if __name__ == "__main__":
    main()
