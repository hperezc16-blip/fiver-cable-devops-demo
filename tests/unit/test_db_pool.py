from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from psycopg import sql
from psycopg_pool import PoolTimeout
from fastapi.testclient import TestClient

from src.common import base

pytestmark = pytest.mark.unit


class FakeConnection:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


class FakePool:
    def __init__(self, **options):
        self.options = options
        self.connection_object = FakeConnection()
        self.opened = False
        self.closed = False
        self.saturated = False

    def open(self, wait):
        self.opened = wait

    def close(self):
        self.closed = True

    @contextmanager
    def connection(self, timeout):
        self.timeout = timeout
        if self.saturated:
            raise PoolTimeout("pool is full")
        yield self.connection_object


@pytest.fixture
def fake_pool(monkeypatch):
    base.close_connection_pool()
    created = []

    def create_pool(**options):
        pool = FakePool(**options)
        created.append(pool)
        return pool

    monkeypatch.setattr(base, "ConnectionPool", create_pool)
    monkeypatch.setenv("DB_POOL_MIN_SIZE", "2")
    monkeypatch.setenv("DB_POOL_MAX_SIZE", "7")
    monkeypatch.setenv("DB_POOL_TIMEOUT_SECONDS", "3")
    yield created
    base.close_connection_pool()


def test_pool_uses_configured_bounds_and_closes(fake_pool):
    base.open_connection_pool()

    pool = fake_pool[0]
    assert pool.options["min_size"] == 2
    assert pool.options["max_size"] == 7
    assert pool.opened is True

    base.close_connection_pool()
    assert pool.closed is True


def test_connection_uses_pool_and_transaction_local_schema(fake_pool):
    base.open_connection_pool()

    with base.get_conn("billing_db") as connection:
        assert connection is fake_pool[0].connection_object

    pool = fake_pool[0]
    assert pool.timeout == 3
    assert len(pool.connection_object.statements) == 1
    assert isinstance(pool.connection_object.statements[0], sql.Composed)


def test_pool_saturation_returns_service_unavailable(fake_pool):
    base.open_connection_pool()
    fake_pool[0].saturated = True

    with pytest.raises(HTTPException) as error:
        with base.get_conn("billing_db"):
            pass

    assert error.value.status_code == 503
    assert error.value.headers["Retry-After"] == "1"


def test_fastapi_lifespan_opens_and_closes_pool(fake_pool):
    app = base.crear_app("test", "billing_db")

    with TestClient(app) as client:
        assert app.state.database_pool is fake_pool[0]
        assert client.get("/health").json()["estado"] == "OK"

    assert app.state.database_pool is None
    assert fake_pool[0].closed is True


def test_invalid_pool_bounds_fail_fast(monkeypatch):
    monkeypatch.setenv("DB_POOL_MIN_SIZE", "6")
    monkeypatch.setenv("DB_POOL_MAX_SIZE", "5")

    with pytest.raises(ValueError, match="Configuración inválida"):
        base.open_connection_pool()