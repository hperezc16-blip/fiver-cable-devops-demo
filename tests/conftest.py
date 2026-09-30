"""Configuración común de la suite de pruebas de Fiver Cable (DevOps 2).

Cada prueba se identifica con el ID del caso del Plan de Pruebas mediante
@pytest.mark.caso("CP-XX", "descripción"); el ID aparece en el reporte HTML.
"""
import os
import time
import uuid

import pytest

AUTH = os.getenv("AUTH_URL", "http://localhost:3000")
CATALOGO = os.getenv("CATALOGO_URL", "http://localhost:3001")
PEDIDOS = os.getenv("PEDIDOS_URL", "http://localhost:3002")
PAGOS = os.getenv("PAGOS_URL", "http://localhost:3003")

TECNICO = (os.getenv("TEST_TECNICO_EMAIL", "tecnico.campo@fivercable.com"),
           os.getenv("TEST_TECNICO_PASSWORD", "Tecnico2026!"))
SUSCRIPTOR = (os.getenv("TEST_SUSCRIPTOR_EMAIL", "hazel.perez@fivercable.com"),
              os.getenv("TEST_SUSCRIPTOR_PASSWORD", "Suscriptor2026!"))


def pytest_configure(config):
    config.addinivalue_line("markers", "caso(id, descripcion): caso del plan de pruebas")


def dsn() -> str:
    return os.getenv("DATABASE_URL", "postgresql://{}:{}@{}:{}/{}".format(
        os.getenv("DB_USER", "postgres"), os.getenv("DB_PASSWORD", "admin123"),
        os.getenv("DB_HOST", "localhost"), os.getenv("DB_PORT", "5432"),
        os.getenv("DB_NAME", "fivercable_db")))


@pytest.fixture
def db():
    """Conexión transaccional: todo se revierte al terminar la prueba (aislamiento)."""
    import psycopg
    from psycopg.rows import dict_row
    conn = psycopg.connect(dsn(), row_factory=dict_row, autocommit=False)
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_commit():
    """Conexión con autocommit para preparar datos que los servicios deben ver."""
    import psycopg
    from psycopg.rows import dict_row
    conn = psycopg.connect(dsn(), row_factory=dict_row, autocommit=True)
    yield conn
    conn.close()


def _login(correo, password) -> str:
    import httpx
    r = httpx.post(f"{AUTH}/api/auth/login", json={"correo": correo, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def token_tecnico() -> str:
    return _login(*TECNICO)


@pytest.fixture(scope="session")
def token_suscriptor() -> str:
    return _login(*SUSCRIPTOR)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def factura_pendiente(db_commit):
    """Crea una factura FEL pendiente nueva para que cada prueba de cobro sea repetible."""
    fila = db_commit.execute(
        """INSERT INTO billing_db.facturas_fel (id_cliente_ref, uuid_sat, serie_fel, numero_fel, monto_total)
           VALUES (1, %s, 'FEL-T', %s, 299.00) RETURNING *""",
        (str(uuid.uuid4()).upper(), str(int(time.time() * 1000))[-8:])).fetchone()
    return fila


# ---- Columna "Caso" en el reporte HTML de pytest-html ----
def pytest_html_results_table_header(cells):
    cells.insert(1, "<th>Caso</th>")


def pytest_html_results_table_row(report, cells):
    cells.insert(1, f"<td>{getattr(report, 'caso_id', '')}</td>")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    m = item.get_closest_marker("caso")
    if m:
        rep.caso_id = m.args[0]
        rep.caso_desc = m.args[1] if len(m.args) > 1 else ""


def pytest_html_report_title(report):
    report.title = "Fiver Cable - Reporte de ejecución del Plan de Pruebas (DevOps 2)"
