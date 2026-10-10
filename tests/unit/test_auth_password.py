from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from src.ms_auth import logic
from src.ms_auth import main as auth_main

pytestmark = pytest.mark.unit


class FakeCursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, password_hash):
        self.password_hash = password_hash

    def execute(self, query, params):
        if query.startswith("SELECT"):
            return FakeCursor({"password_hash": self.password_hash})
        self.password_hash = params[0]
        return FakeCursor()


@pytest.fixture
def auth_context(monkeypatch):
    connection = FakeConnection(logic.hash_password("Actual2026x"))

    @contextmanager
    def fake_get_conn(schema):
        assert schema == auth_main.ESQUEMA
        yield connection

    monkeypatch.setattr(auth_main, "get_conn", fake_get_conn)
    return connection


@pytest.mark.caso("CP-36", "El usuario autenticado puede cambiar su contraseña actual")
def test_change_password_replaces_hash(auth_context):
    result = auth_main.cambiar_password(
        auth_main.CambioPassword(
            password_actual="Actual2026x",
            password_nueva="NuevaClave2026",
        ),
        {"sub": "1"},
    )

    assert result == {"mensaje": "Contraseña actualizada"}
    assert logic.verificar_password("NuevaClave2026", auth_context.password_hash)
    assert not logic.verificar_password("Actual2026x", auth_context.password_hash)


@pytest.mark.caso("CP-37", "El cambio rechaza una contraseña actual incorrecta")
def test_change_password_rejects_wrong_current_password(auth_context):
    with pytest.raises(HTTPException) as error:
        auth_main.cambiar_password(
            auth_main.CambioPassword(
                password_actual="Incorrecta2026",
                password_nueva="NuevaClave2026",
            ),
            {"sub": "1"},
        )

    assert error.value.status_code == 401
    assert logic.verificar_password("Actual2026x", auth_context.password_hash)


@pytest.mark.caso("CP-38", "El cambio rechaza contraseñas débiles o repetidas")
def test_change_password_rejects_weak_or_reused_password(auth_context):
    with pytest.raises(HTTPException) as weak_error:
        auth_main.cambiar_password(
            auth_main.CambioPassword(
                password_actual="Actual2026x",
                password_nueva="weak",
            ),
            {"sub": "1"},
        )
    assert weak_error.value.status_code == 422

    with pytest.raises(HTTPException) as reused_error:
        auth_main.cambiar_password(
            auth_main.CambioPassword(
                password_actual="Actual2026x",
                password_nueva="Actual2026x",
            ),
            {"sub": "1"},
        )
    assert reused_error.value.status_code == 422