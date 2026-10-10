"""Pruebas de RENDIMIENTO básicas (línea base del Sprint 2).

Umbrales configurables por variables de entorno para que el pipeline los ajuste por entorno.
"""
import asyncio
import os
import statistics
import time

import httpx
import pytest

from tests.conftest import CATALOGO, PAGOS, auth

pytestmark = pytest.mark.performance
P95_MAX_MS = float(os.getenv("PERF_P95_MAX_MS", "300"))
PERF_CONCURRENCY = int(os.getenv("PERF_CONCURRENCY", "20"))
PERF_REQUESTS = int(os.getenv("PERF_REQUESTS", str(max(200, PERF_CONCURRENCY * 2))))


def _medir(cliente, url, headers=None):
    t0 = time.perf_counter()
    r = cliente.get(url, headers=headers)
    return (time.perf_counter() - t0) * 1000, r.status_code


async def _medir_concurrente(url, headers=None):
    limites = httpx.Limits(
        max_connections=PERF_CONCURRENCY,
        max_keepalive_connections=PERF_CONCURRENCY,
    )
    async with httpx.AsyncClient(timeout=10, limits=limites) as cliente:
        async def medir_una():
            inicio = time.perf_counter()
            respuesta = await cliente.get(url, headers=headers)
            return (time.perf_counter() - inicio) * 1000, respuesta.status_code

        return await asyncio.gather(*(medir_una() for _ in range(PERF_REQUESTS)))


@pytest.mark.caso("CP-25", "Catálogo de planes: 200 solicitudes secuenciales con p95 < umbral")
def test_latencia_catalogo():
    with httpx.Client(timeout=5) as c:
        muestras = [_medir(c, f"{CATALOGO}/api/planes") for _ in range(200)]
    tiempos = sorted(t for t, _ in muestras)
    p95 = tiempos[int(len(tiempos) * 0.95) - 1]
    print(f"\nCP-25 promedio={statistics.mean(tiempos):.1f} ms p95={p95:.1f} ms max={max(tiempos):.1f} ms")
    assert all(s == 200 for _, s in muestras)
    assert p95 < P95_MAX_MS


@pytest.mark.caso("CP-26", "Consulta de facturas con concurrencia configurable sin errores")
def test_concurrencia_facturas(token_tecnico):
    url = f"{PAGOS}/api/facturas?id_cliente=2"
    resultados = asyncio.run(_medir_concurrente(url, auth(token_tecnico)))
    tiempos = sorted(t for t, _ in resultados)
    p95 = tiempos[int(len(tiempos) * 0.95) - 1]
    errores = sum(1 for _, s in resultados if s != 200)
    print(f"\nCP-26 solicitudes={PERF_REQUESTS} concurrencia={PERF_CONCURRENCY} p95={p95:.1f} ms errores={errores}")
    assert errores == 0
    assert p95 < P95_MAX_MS * 3
