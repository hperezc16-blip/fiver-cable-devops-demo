"""Captura evidencias del portal integrado (ms_pagos /portal) contra el entorno en ejecución.

Requiere los contenedores arriba con datos semilla recién cargados:
    docker compose down -v && docker compose up -d --build --wait
    python docs/evidencias/capturar_evidencias.py

Las contraseñas se leen de las variables TEST_* (o sus valores de demostración) y
nunca quedan visibles: el campo de contraseña del portal es de tipo password.
"""
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

AUTH = os.getenv("AUTH_URL", "http://localhost:3000")
PAGOS = os.getenv("PAGOS_URL", "http://localhost:3003")
TECNICO = (os.getenv("TEST_TECNICO_EMAIL", "tecnico.campo@fivercable.com"),
           os.getenv("TEST_TECNICO_PASSWORD", "Tecnico2026!"))
SUSCRIPTOR = (os.getenv("TEST_SUSCRIPTOR_EMAIL", "hazel.perez@fivercable.com"),
              os.getenv("TEST_SUSCRIPTOR_PASSWORD", "Suscriptor2026!"))
SALIDA = Path(__file__).parent / "capturas"


def navegador() -> webdriver.Chrome:
    opciones = webdriver.ChromeOptions()
    if os.getenv("HEADLESS", "1") == "1":
        opciones.add_argument("--headless=new")
    opciones.add_argument("--window-size=1100,1000")
    return webdriver.Chrome(options=opciones)


def captura(d, nombre: str) -> None:
    time.sleep(0.6)
    d.save_screenshot(str(SALIDA / f"{nombre}.png"))
    print("captura", nombre)


def esperar_texto(d, elemento_id: str, texto: str) -> None:
    WebDriverWait(d, 10).until(EC.text_to_be_present_in_element((By.ID, elemento_id), texto))


def login(d, correo: str, password: str) -> None:
    d.get(f"{PAGOS}/portal")
    d.find_element(By.ID, "correo").send_keys(correo)
    d.find_element(By.ID, "password").send_keys(password)
    d.find_element(By.ID, "btn-login").click()


def buscar(d, id_cliente: int, metodo: str = "Efectivo", autorizacion: str = "") -> None:
    campo = d.find_element(By.ID, "id-cliente")
    campo.clear()
    campo.send_keys(str(id_cliente))
    Select(d.find_element(By.ID, "metodo")).select_by_value(metodo)
    aut = d.find_element(By.ID, "autorizacion")
    aut.clear()
    if autorizacion:
        aut.send_keys(autorizacion)
    d.find_element(By.ID, "btn-buscar").click()


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    d = navegador()
    espera = WebDriverWait(d, 10)
    try:
        # Disponibilidad: /health de los cuatro microservicios
        for nombre, puerto in (("auth", 3000), ("catalogo", 3001), ("pedidos", 3002), ("pagos", 3003)):
            d.get(f"{PAGOS.rsplit(':', 1)[0]}:{puerto}/health")
            captura(d, f"E01_health_ms_{nombre}")
        d.get(f"{PAGOS}/docs")
        espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".opblock")))
        captura(d, "E02_openapi_ms_pagos")

        # Seguridad: la API rechaza solicitudes sin token
        d.get(f"{PAGOS}/api/facturas?id_cliente=1")
        captura(d, "S01_api_sin_token_401")

        # Manual: inicio de sesión
        d.get(f"{PAGOS}/portal")
        espera.until(EC.visibility_of_element_located((By.ID, "correo")))
        captura(d, "M01_inicio_sesion")
        login(d, TECNICO[0], "ClaveIncorrecta1")
        esperar_texto(d, "login-msg", "Credenciales")
        captura(d, "S02_login_credenciales_invalidas")

        # Manual: técnico busca facturas pendientes del cliente 2
        login(d, TECNICO[0], TECNICO[1])
        espera.until(EC.visibility_of_element_located((By.ID, "seccion-cobro")))
        captura(d, "M02_sesion_tecnico")
        buscar(d, 2, "Tarjeta")
        espera.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.cobrar")))
        captura(d, "M03_facturas_pendientes")

        # Validación: tarjeta sin código de autorización es rechazada
        d.find_element(By.CSS_SELECTOR, "button.cobrar").click()
        esperar_texto(d, "cobro-msg", "autorización")
        captura(d, "S03_cobro_rechazado_sin_autorizacion")

        # Manual: cobro exitoso en efectivo y recibo
        buscar(d, 2, "Efectivo")
        espera.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.cobrar")))
        d.find_element(By.CSS_SELECTOR, "button.cobrar").click()
        espera.until(EC.presence_of_element_located((By.ID, "id-transaccion")))
        captura(d, "M04_cobro_exitoso_recibo")

        # Integridad: la factura pagada ya no aparece como pendiente
        buscar(d, 2, "Efectivo")
        time.sleep(1)
        captura(d, "M05_factura_ya_no_pendiente")

        # Cambio de contraseña (formulario, sin enviar)
        d.find_element(By.ID, "btn-toggle-password").click()
        captura(d, "M06_formulario_cambio_password")
        d.find_element(By.ID, "btn-logout").click()

        # Autorización: el portal no admite al rol Suscriptor (la API además responde 403)
        login(d, SUSCRIPTOR[0], SUSCRIPTOR[1])
        esperar_texto(d, "login-msg", "personal técnico")
        captura(d, "S04_suscriptor_bloqueado_en_portal")
    finally:
        d.quit()


if __name__ == "__main__":
    main()
