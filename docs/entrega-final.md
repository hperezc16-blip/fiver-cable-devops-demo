# Entrega final: Fiver Cable, cobro digital en campo

**Proyecto:** Transformación digital del proceso de cobro en campo  
**Curso:** Seminario de Tecnologías de Información 2026, Universidad Mariano Gálvez de Guatemala  
**Empresa:** Fiver Cable, proveedor de internet y televisión por fibra óptica  
**Equipo:** Hazel Ruvi Perez Carcamo (0900-21-13727), Byron Enrique Morales (0900-1015162), Luis Oswaldo Reyes (0900-98-2342)  
**Repositorio:** Azure Repos `Fiver Cable DevOps`  
**Fecha de las evidencias:** 10 de octubre de 2026

Todas las capturas y salidas de este documento provienen de la ejecución real del sistema en el equipo del grupo. Las cuentas y los datos que aparecen son de demostración (`db/init/02_seed.sql`). No se muestran contraseñas, tokens, claves ni cadenas de conexión.

## Contenido

1. [Proceso seleccionado](#1-proceso-seleccionado)
2. [Solución desarrollada](#2-solución-desarrollada)
3. [Código fuente](#3-código-fuente)
4. [Puesta en producción](#4-puesta-en-producción)
5. [Pruebas](#5-pruebas)
6. [Manual de usuario](#6-manual-de-usuario)
7. [Seguridad de la solución](#7-seguridad-de-la-solución)
8. [Resultados](#8-resultados)
9. [Conclusiones y anexos](#9-conclusiones-y-anexos)
10. [Guion de la exposición](#10-guion-de-la-exposición-10-minutos)

---

## 1. Proceso seleccionado

### Proceso actual

Cuando un cliente de Fiver Cable tiene facturas pendientes, su servicio puede quedar en estado *Moroso* o *Suspendido*. Durante una visita técnica, el cliente suele querer pagar en ese momento. Hoy el técnico recibe el dinero, lo anota de forma manual y el pago se registra después en oficina. Hasta que facturación procesa ese registro, la factura sigue apareciendo como pendiente y el cliente sigue sin servicio.

### Problema identificado

- El pago queda registrado con retraso, porque depende de que el técnico lo entregue y alguien lo transcriba.
- La transcripción permite errores de monto, de factura o de cliente.
- No existe un comprobante con identificador único en el momento del cobro.
- La conciliación diaria entre lo cobrado en campo y lo registrado es manual.
- Una misma factura puede quedar expuesta a cobrarse dos veces.

### Justificación de la automatización

Es un proceso frecuente, con reglas claras (una factura, un monto, un método de pago) y directamente ligado al ingreso de la empresa. Si se registra en el momento y en una sola operación, se elimina la transcripción, se impide el cobro duplicado, se emite el recibo de inmediato y el cierre diario se calcula solo. Por eso el equipo lo eligió como proceso prioritario de la transformación digital.

> Alcance de la medición: el equipo no levantó una línea base cuantitativa (tiempos o errores del proceso manual). Los beneficios de la sección 8 se presentan como mejoras del flujo comprobadas en el sistema, no como ahorro medido.

---

## 2. Solución desarrollada

### Descripción

Es una plataforma de cuatro microservicios con un **portal web de cobro en campo**. El técnico inicia sesión desde el celular o la computadora, busca las facturas pendientes del cliente, elige el método de pago y registra el cobro. El sistema valida el pago, lo guarda, marca la factura como *Pagado* y muestra el número de recibo.

### Funcionalidades principales

| Funcionalidad | Servicio | Endpoint / pantalla |
|---|---|---|
| Inicio de sesión con JWT y roles | `ms_auth` | `POST /api/auth/login`, portal |
| Cambio de contraseña autenticado | `ms_auth` | `PUT /api/auth/cambiar-password`, portal |
| Registro de suscriptores con validación de NIT/DPI y política de contraseña | `ms_auth` | `POST /api/auth/registro` |
| Cambio de estado del servicio, con transiciones válidas y auditoría | `ms_auth` | `PATCH /api/clientes/{id}/estado` |
| Consulta de facturas pendientes | `ms_pagos` | `GET /api/facturas`, portal |
| **Registro de cobro con recibo** | `ms_pagos` | `POST /api/pagos`, portal |
| Cierre diario de pagos por método | `ms_pagos` | `GET /api/pagos/cierre-diario` |
| Planes, equipos ONU y señal óptica | `ms_catalogo` | `/api/planes`, `/api/onus` |
| Tickets de soporte con prioridad y SLA | `ms_pedidos` | `/api/tickets` |

### Tecnologías

| Capa | Tecnología |
|---|---|
| Lenguaje y API | Python 3.11, FastAPI, Pydantic |
| Base de datos | PostgreSQL 16, con un esquema por microservicio |
| Seguridad | PyJWT (HS256), bcrypt |
| Contenedores | Docker, Docker Compose |
| CI/CD | Azure Pipelines (`azure-pipelines.yml`), Jenkins (`Jenkinsfile`) |
| Nube (staging) | Azure Container Apps, Azure Container Registry, Azure Database for PostgreSQL (`infra/azure/deploy-staging.sh`) |
| Pruebas | Pytest, httpx, Selenium, pytest-cov, pytest-html, Ruff |

### Arquitectura

```mermaid
flowchart LR
    T[Técnico<br/>navegador] -->|HTTPS + JWT| P[ms_pagos :3003<br/>portal y API]
    T -->|login| A[ms_auth :3000]
    S[Suscriptor] -->|JWT| A
    S -->|sus facturas| P
    ADM[Administrador] --> A & P & C[ms_catalogo :3001] & D[ms_pedidos :3002]
    subgraph PG[PostgreSQL 16 - fivercable_db]
      U[(usuarios_db)]
      B[(billing_db)]
      R[(red_db)]
      SO[(soporte_db)]
    end
    A --> U
    P --> B
    C --> R
    D --> SO
```

### Flujo principal (cobro en campo)

```mermaid
sequenceDiagram
    actor Tecnico
    participant Portal as Portal (ms_pagos)
    participant Auth as ms_auth
    participant Pagos as API ms_pagos
    participant DB as billing_db
    Tecnico->>Portal: correo y contraseña
    Portal->>Auth: POST /api/auth/login
    Auth-->>Portal: JWT firmado (rol Tecnico, 60 min)
    Tecnico->>Portal: código de cliente
    Portal->>Pagos: GET /api/facturas?estado=Pendiente + JWT
    Pagos->>DB: SELECT parametrizado
    DB-->>Portal: facturas pendientes
    Tecnico->>Portal: Cobrar
    Portal->>Pagos: POST /api/pagos + JWT
    Pagos->>DB: SELECT ... FOR UPDATE (bloquea la factura)
    Pagos->>Pagos: valida rol, método, autorización y monto exacto
    Pagos->>DB: INSERT pago
    DB->>DB: trigger: factura = Pagado
    Pagos-->>Portal: recibo FC-AAAAMMDDhhmmss-XXXXXXXX
```

---

## 3. Código fuente

El código está en este repositorio. Su organización:

```
src/
  common/base.py      JWT, roles, pool de conexiones, CORS, manejo de errores y /health
  ms_auth/            main.py (API) + logic.py (reglas puras: NIT, contraseña, transiciones)
  ms_catalogo/        planes, ONU, señal óptica
  ms_pedidos/         tickets, prioridad y SLA
  ms_pagos/           main.py (API), logic.py (monto, método, id de transacción), portal.html
db/init/              01_schema.sql (esquemas, restricciones, vistas, triggers) y 02_seed.sql
docker/               un Dockerfile por servicio (imagen slim, usuario sin privilegios, healthcheck)
tests/                unit, integration, system, acceptance, security, performance
infra/azure/          despliegue de staging en Azure
docs/evidencias/      capturas, reporte de pruebas y script que las genera
```

### Componentes principales

- **`src/common/base.py`**: cada servicio se crea con `crear_app()`, que registra el pool de conexiones, el CORS restringido por la variable `CORS_ORIGINS`, un manejador que oculta las trazas internas y el endpoint `/health`. `usuario_actual()` valida el JWT y `requiere_rol()` protege las rutas por rol. `get_conn()` fija el `search_path` del esquema del servicio en cada transacción.
- **Separación API/lógica**: cada `main.py` contiene solo las rutas HTTP y el SQL. Las reglas de negocio están en `logic.py`, que no depende de la base de datos y por eso se puede probar con pruebas unitarias.
- **`src/ms_pagos/main.py` → `registrar_pago`**: es el núcleo del proceso. Exige el rol Técnico o Administrador, valida el método y el código de autorización, bloquea la factura con `FOR UPDATE`, rechaza facturas que no estén pendientes, exige que el monto coincida con la factura e inserta el pago con un identificador generado por `secrets`.
- **`db/init/01_schema.sql`**: contiene las restricciones `CHECK` sobre estados, roles y montos, las claves foráneas, el trigger `trg_procesar_pago_exitoso` (que marca la factura como pagada), el trigger `trg_auditar_cliente` (que registra en la auditoría cada cambio de estado) y la vista `vw_cierre_diario_pagos`.
- **`src/ms_pagos/portal.html`**: es una interfaz de una sola página. Escapa todo dato antes de insertarlo en el HTML y guarda el token solo en memoria (no usa `localStorage`).

---

## 4. Puesta en producción

### Entorno utilizado

La aplicación se ejecuta en contenedores con Docker Compose: PostgreSQL 16, Redis y los cuatro microservicios, cada uno con su healthcheck. Para la demostración se usó Docker Desktop 29.4 sobre Windows 11.

```powershell
Copy-Item .env.example .env      # luego reemplazar los valores de demostración
docker compose up -d --build --wait
docker compose ps
```

Salida obtenida:

```
NAME             STATUS                    PORTS
fiver_postgres   Up 30 seconds (healthy)   0.0.0.0:5432->5432/tcp
fiver_redis      Up 30 seconds             0.0.0.0:6379->6379/tcp
ms_auth          Up 18 seconds (healthy)   0.0.0.0:3000->3000/tcp
ms_catalogo      Up 18 seconds (healthy)   0.0.0.0:3001->3001/tcp
ms_pagos         Up 18 seconds (healthy)   0.0.0.0:3003->3003/tcp
ms_pedidos       Up 18 seconds (healthy)   0.0.0.0:3002->3002/tcp
```

| URL | Uso |
|---|---|
| `http://localhost:3003/portal` | Portal de cobro en campo |
| `http://localhost:3000/docs` … `:3003/docs` | Documentación OpenAPI de cada servicio |
| `http://localhost:300X/health` | Estado del servicio y de su conexión a la base de datos |

### Proceso de despliegue (CI/CD)

```mermaid
flowchart LR
    F[feature/*] -->|Pull Request| DV[develop] -->|Pull Request| M[main]
    M --> B[Build<br/>ruff + unitarias + imágenes]
    B --> TS[Test<br/>suite completa, reporte HTML, cobertura]
    TS --> DS[Deploy Staging<br/>solo main]
    DS -->|por defecto| CO[Docker Compose en el agente + smoke tests]
    DS -->|desplegarEnAzure=true| AZ[Azure Container Apps + PostgreSQL Flexible + smoke tests]
```

- En `azure-pipelines.yml`, cada push o PR a `develop`/`main` ejecuta las etapas Build y Test. Solo `main` llega a Deploy Staging, que se ejecuta en el Environment `fivercable-staging`.
- `infra/azure/deploy-staging.sh` es idempotente. Crea el grupo de recursos, ACR, PostgreSQL Flexible Server y Container Apps, carga el esquema, publica las imágenes y verifica `/health` de los cuatro servicios. La contraseña de PostgreSQL y el secreto JWT se generan en cada despliegue y se guardan como *secrets* de Container Apps (`secretref:`), no en el repositorio.

### Evidencias de funcionamiento

| `/health` ms_auth | `/health` ms_pagos |
|---|---|
| ![health auth](evidencias/capturas/E01_health_ms_auth.png) | ![health pagos](evidencias/capturas/E01_health_ms_pagos.png) |

Las capturas de `ms_catalogo` y `ms_pedidos` también están en [evidencias/capturas](evidencias/capturas/). Las cuatro respuestas muestran `"estado":"OK","db":true`.

![OpenAPI de ms_pagos](evidencias/capturas/E02_openapi_ms_pagos.png)

> **Azure (completar si se ejecutó):** si el equipo corrió el pipeline con `desplegarEnAzure = true`, agregar aquí la captura del run exitoso (número de build y fecha), la URL `https://ms-pagos.<…>.azurecontainerapps.io/portal` y `/health` de los cuatro servicios, ocultando el ID de suscripción. Si no se ejecutó, la demostración en clase se presenta como **ambiente Docker de staging** y Azure como despliegue configurado.

---

## 5. Pruebas

La suite usa Pytest. Cada caso lleva el ID del plan de pruebas (CP-01 a CP-39), que se muestra en el reporte HTML.

```powershell
python -m pytest --html=reports/reporte-pruebas.html --self-contained-html --cov=src
```

### Resultados de la ejecución del 10/10/2026 (commit `a93a415` más los cambios de esta entrega)

| Tipo | Marcador | Resultado |
|---|---|---|
| Unitarias (reglas de negocio, contraseña, JWT, pool) | `unit` | 30 aprobadas |
| Integración con la base de datos (triggers, procedimientos, restricciones) | `integration` | 5 aprobadas |
| Sistema (flujo de cobro completo por API, cobro duplicado, monto) | `system` | 9 aprobadas |
| Aceptación con Selenium (prototipo: cliente, técnico, administrador, jefatura, secretaría) | `acceptance` | 8 aprobadas |
| Seguridad (token ausente o manipulado, roles, aislamiento, inyección SQL) | `security` | 5 aprobadas |
| Rendimiento | `performance` | 1 aprobada, **1 fallida** |
| **Total** | | **58 aprobadas, 1 fallida** |

- **Análisis estático:** `ruff check` dio *All checks passed*.
- **Rendimiento:** CP-25 (latencia individual) aprobó, con un promedio de 6.3 ms, p95 de 8.5 ms y máximo de 51.3 ms. CP-26 (200 solicitudes con 20 concurrentes) **falló**: el p95 fue de 1509 ms frente a un límite de 900 ms, aunque hubo **0 errores**. Todas las solicitudes respondieron bien, pero en cola. La causa probable es el pool de conexiones limitado a 5 por servicio y Docker Desktop en Windows. El ajuste se detalla en la sección 9.
- **Cobertura:** 50 % del total. Las reglas de negocio tienen entre 91 % y 100 %. Los `main.py` aparecen con 0 % porque las pruebas de sistema los ejecutan dentro de los contenedores, donde la herramienta de cobertura del host no los mide. Esos módulos sí se ejercitan en las pruebas de sistema y seguridad.

Reporte completo: [evidencias/reporte-pruebas.html](evidencias/reporte-pruebas.html), con el único token de demostración que aparecía en un traceback ya oculto. Las capturas de Selenium del prototipo están en [evidencias/capturas-prototipo](evidencias/capturas-prototipo/).

### Pruebas funcionales del flujo de cobro (portal integrado)

| Caso | Resultado esperado | Obtenido | Evidencia |
|---|---|---|---|
| Buscar facturas pendientes del cliente 2 | Lista FEL-A-1002 y FEL-A-1003 | ✔ | M03 |
| Cobrar con tarjeta sin código de autorización | Rechazo | ✔ *"El método de pago requiere código de autorización"* | S03 |
| Cobrar FEL-A-1002 en efectivo | Recibo y estado Pagado | ✔ Recibo `FC-20261010180358-FFF0854E` | M04 |
| Volver a buscar | FEL-A-1002 ya no aparece como pendiente | ✔ | M05 |
| Cobrar de nuevo FEL-A-1002 por API | 409 | ✔ *"La factura ya está en estado Pagado"* | Anexo A |

Estado en la base de datos después del cobro:

```
 id_pago | id_factura |  id_transaccion_pasarela   | monto_pagado | metodo_pago
---------+------------+----------------------------+--------------+------------
       1 |          2 | FC-20261010180358-FFF0854E |       499.00 | Efectivo

 id_factura |  factura   | id_cliente_ref | monto_total | estado_pago
------------+------------+----------------+-------------+------------
          1 | FEL-A-1001 |              1 |      299.00 | Pendiente
          2 | FEL-A-1002 |              2 |      499.00 | Pagado
          3 | FEL-A-1003 |              2 |      499.00 | Pendiente

Cierre diario (vw_cierre_diario_pagos)
   fecha    | metodo_pago | total_transacciones | total_recaudado
 2026-10-10 | Efectivo    |                   1 |          499.00
```

---

## 6. Manual de usuario

### Requisitos para acceder

- Un navegador actualizado (Chrome, Edge o Firefox), en computadora o celular.
- La dirección del portal: `http://localhost:3003/portal` en el ambiente local, o la URL de staging que entregue el equipo.
- Una cuenta con rol **Técnico** o **Administrador**, que entrega Administración. Las cuentas de suscriptor no pueden usar el portal de cobro.

### Paso 1. Iniciar sesión

Escriba su correo y su contraseña y seleccione **Iniciar sesión**. La contraseña nunca se muestra en pantalla.

![Inicio de sesión](evidencias/capturas/M01_inicio_sesion.png)

Si los datos son incorrectos, el sistema responde con *Credenciales inválidas* y no indica cuál de los dos campos falló:

![Credenciales inválidas](evidencias/capturas/S02_login_credenciales_invalidas.png)

Si olvidó su contraseña, seleccione **¿Olvidaste tu contraseña?** y solicite el restablecimiento a Administración.

### Paso 2. Buscar las facturas del cliente

1. Escriba el **código de cliente**.
2. Elija el **método de pago**: Efectivo, Tarjeta o Transferencia.
3. Si el método es Tarjeta o Transferencia, escriba el **código de autorización** del voucher o de la transferencia.
4. Seleccione **Buscar facturas**.

![Facturas pendientes](evidencias/capturas/M03_facturas_pendientes.png)

### Paso 3. Cobrar

Antes de cobrar, compruebe con el cliente el número de factura y el monto. Luego seleccione **Cobrar Q …** **una sola vez**. El cobro liquida la factura completa.

Si falta información, el sistema rechaza el cobro y explica el motivo:

![Cobro rechazado](evidencias/capturas/S03_cobro_rechazado_sin_autorizacion.png)

Cuando el cobro se registra, la factura cambia a **Pagado** y aparece el número de **recibo**. Entréguelo o dícteselo al cliente.

![Cobro exitoso](evidencias/capturas/M04_cobro_exitoso_recibo.png)

Si vuelve a buscar, la factura pagada ya no aparece entre las pendientes:

![Factura ya no pendiente](evidencias/capturas/M05_factura_ya_no_pendiente.png)

### Paso 4. Cambiar la contraseña

Seleccione **Cambiar contraseña**. Escriba la contraseña actual, la nueva y la confirmación. La nueva contraseña debe tener al menos 8 caracteres, con una mayúscula, una minúscula y un número, y debe ser distinta de la actual.

![Cambio de contraseña](evidencias/capturas/M06_formulario_cambio_password.png)

### Paso 5. Cerrar sesión

Seleccione **Cerrar sesión** al terminar, sobre todo en equipos compartidos. La sesión expira sola a los 60 minutos.

### Buenas prácticas de uso seguro

- No comparta su cuenta ni anote la contraseña en el equipo.
- No repita un cobro si hubo un error de red. Busque primero la factura: si ya no aparece como pendiente, el cobro quedó registrado.
- Verifique la identidad del cliente antes de cobrar.
- Reporte a Administración cualquier cobro que no reconozca en el cierre diario.

---

## 7. Seguridad de la solución

En esta sección, cada control tiene su evidencia real: una captura, código, configuración o el resultado de una prueba.

### 7.1 Requerimientos de seguridad

| Requerimiento | Cómo se cumple | Evidencia |
|---|---|---|
| **Autenticación** | Login con contraseña verificada con bcrypt. Se emite un JWT HS256 que expira a los 60 min y se valida su firma en cada solicitud. | `src/common/base.py` (`crear_token`, `usuario_actual`), S01, S02, Anexo A, CP-22 |
| **Autorización** | `requiere_rol("Tecnico","Administrador")` en cobro, cierre y cambio de estado. El suscriptor solo puede consultar lo propio. | `src/ms_pagos/main.py`, Anexo A (403), S04, CP-23 |
| **Privacidad** | El hash de la contraseña nunca se devuelve. Un suscriptor no puede ver datos de otro cliente. Las capturas usan datos ficticios. | `obtener_cliente` en `ms_auth/main.py`, Anexo A |
| **Integridad** | El monto debe coincidir con la factura. La factura se bloquea con `FOR UPDATE`. Hay restricciones `CHECK` y FK, y el trigger cambia el estado. Una factura no se cobra dos veces. | `ms_pagos/main.py`, `01_schema.sql`, Anexo A (409, 422) |
| **Disponibilidad** | Healthchecks en Docker y `/health`. El pool de conexiones es acotado y devuelve 503 con `Retry-After` si se agota. Container Apps limita las réplicas. | `base.py`, `docker-compose.yml`, `deploy-staging.sh`, E01 |

### 7.2 Arquitectura y UML: roles, permisos, límites de confianza y flujos críticos

**Matriz de roles y permisos (lo que la API aplica realmente):**

| Operación | Suscriptor | Técnico | Administrador |
|---|---|---|---|
| Iniciar sesión / cambiar su contraseña | ✔ | ✔ | ✔ |
| Ver su perfil y sus facturas | ✔ (solo las propias) | ✔ | ✔ |
| Ver facturas de otro cliente | ✘ 403 | ✔ | ✔ |
| Registrar cobro | ✘ 403 | ✔ | ✔ |
| Cierre diario | ✘ 403 | ✔ | ✔ |
| Cambiar el estado del servicio | ✘ 403 | ✔ | ✔ |
| Usar el portal de cobro | ✘ bloqueado | ✔ | ✔ |

**Diagrama de casos de uso por rol:**

```mermaid
flowchart LR
    S((Suscriptor)) --> UC1[Iniciar sesión]
    S --> UC2[Consultar sus facturas]
    S --> UC7[Cambiar contraseña]
    T((Técnico)) --> UC1
    T --> UC3[Buscar facturas de un cliente]
    T --> UC4[Registrar cobro]
    T --> UC5[Ver cierre diario]
    T --> UC6[Cambiar estado del servicio]
    T --> UC7
    A((Administrador)) --> UC3 & UC4 & UC5 & UC6 & UC7
```

**Límites de confianza:**

```mermaid
flowchart TB
    subgraph Z0[Zona no confiable: Internet / dispositivo del técnico]
      N[Navegador / portal]
    end
    subgraph Z1[Zona de aplicación: contenedores]
      A[ms_auth]:::svc
      P[ms_pagos]:::svc
      C[ms_catalogo]:::svc
      D[ms_pedidos]:::svc
    end
    subgraph Z2[Zona de datos]
      DB[(PostgreSQL)]
    end
    subgraph Z3[Zona de administración / CI-CD]
      AZ[Azure DevOps + secretos]
    end
    N -- "LC1: JWT + validación Pydantic + CORS" --> A & P
    A & P & C & D -- "LC2: SQL parametrizado, search_path por esquema" --> DB
    AZ -- "LC3: service connection, secretos enmascarados" --> Z1
    classDef svc fill:#eef
```

- **LC1:** ninguna entrada del navegador se considera confiable. Toda ruta de negocio exige un JWT válido, Pydantic valida los tipos y rangos, y CORS solo permite los orígenes configurados.
- **LC2:** los servicios no concatenan SQL y cada uno trabaja dentro de su esquema.
- **LC3:** los secretos de despliegue solo existen en Azure DevOps y en Container Apps.

**Flujo crítico (registro del cobro) con sus controles:** este es el diagrama de secuencia de la sección 2. Los controles se aplican en este orden: JWT válido → rol permitido → método permitido → autorización presente si es tarjeta o transferencia → factura existente y bloqueada → estado Pendiente → monto exacto → inserción → trigger.

### 7.3 Datos y base de datos

| Tema | Implementación | Evidencia |
|---|---|---|
| Protección de la información | Contraseñas con bcrypt (cost 10, con sal). Las consultas no devuelven el hash. | Consulta: `hash_bcrypt = $2b$10$…` en los 3 usuarios (Anexo B) |
| Integridad | `CHECK` sobre estados, roles y montos (`monto_pagado > 0`). `FOREIGN KEY ... ON DELETE RESTRICT` de pagos a facturas. `UNIQUE` en correo, `uuid_sat` y MAC. | `db/init/01_schema.sql`, CP integración (MAC única) |
| Auditoría | El trigger `trg_auditar_cliente` registra el estado anterior y el nuevo en `auditoria_usuarios` | Anexo B: dos registros reales generados por la API |
| Separación | Un esquema por microservicio. `get_conn` fija `SET LOCAL search_path` solo al esquema del servicio. | `src/common/base.py` |
| Credenciales | Se leen de variables de entorno o de *secrets*. `.env` está en `.gitignore`. En Azure, la contraseña de PostgreSQL es aleatoria en cada despliegue. | `.gitignore`, `deploy-staging.sh` |
| Mínimo privilegio | **Pendiente:** los cuatro servicios se conectan con el mismo usuario administrador. Plan: un rol de PostgreSQL por esquema con `GRANT` limitado. | Hallazgo H2 |
| Respaldos | **Pendiente en local.** Azure PostgreSQL Flexible Server incluye respaldos automáticos (7 días por defecto). Falta documentar una prueba de restauración. | Hallazgo H4 |

### 7.4 DevOps: accesos, repositorio, secretos, dependencias y CI/CD

| Tema | Implementación | Evidencia |
|---|---|---|
| Control de acceso al repositorio | Repositorio privado en Azure Repos. Flujo `feature/*` → PR a `develop` → PR a `main`. Solo `main` despliega. | `README.md`, `azure-pipelines.yml` (`condition: ... refs/heads/main`) |
| Secretos | No hay secretos reales en el repositorio. `.env` está ignorado. El pipeline enmascara los valores generados (`##vso[task.setsecret]`) y Container Apps usa `secretref:`. Jenkins toma `JWT_SECRET` de `credentials()`. | `deploy-staging.sh`, `Jenkinsfile`, `git check-ignore .env` → `.gitignore:2` |
| Dependencias | Versiones fijadas con `==` en `requirements*.txt`. Imagen base `python:3.11-slim`. | `requirements.txt` |
| Contenedores | Los servicios corren como un usuario sin privilegios (`USER appuser`) y tienen `HEALTHCHECK`. | `docker/Dockerfile.*` |
| Seguridad del pipeline | Calidad antes de construir: Ruff y pruebas unitarias con fallo rápido. La suite de seguridad corre en cada build. Deploy en un Environment (`fivercable-staging`) que admite aprobaciones manuales. | `azure-pipelines.yml` |
| Pendiente | Escaneo de vulnerabilidades de dependencias e imágenes (`pip-audit`, Trivy) y políticas de rama obligatorias configuradas en Azure Repos. | Hallazgo H5 |

### 7.5 Aplicación: entradas, sesiones, permisos, errores y registros

| Tema | Implementación | Evidencia |
|---|---|---|
| Validación de entradas | Modelos Pydantic: `id_factura > 0`, teléfono `^\d{8,15}$`, longitudes máximas. NIT con dígito verificador, correo y política de contraseña en `logic.py`. Métodos de pago en lista blanca. | Anexo A: inyección `1 OR 1=1` → 422, "Bitcoin" → 422, contraseña débil → 422 |
| Inyección SQL | Todas las consultas usan parámetros `%s` de psycopg. El nombre del esquema se compone con `sql.Identifier`. | `ms_*/main.py`, CP-24 |
| XSS | El portal escapa todos los datos con `escapar()` antes de insertarlos en el DOM | `portal.html` |
| Sesiones | JWT con `exp` de 60 min y algoritmo fijo (`algorithms=["HS256"]`, no acepta `none`). El token vive solo en memoria y se borra al cerrar sesión. | `base.py`, S01, Anexo A (token manipulado → 401) |
| Permisos | Dependencias `requiere_rol` y verificación de propiedad (`sub == id_cliente`) | Anexo A (403) |
| Manejo de errores | El manejador global devuelve `{"detail":"Error interno del servicio"}` sin traza. Los mensajes de login no revelan si el correo existe. | `base.py`, S02 |
| Registros | Auditoría de cambios de estado en la base de datos. Cada pago guarda la fecha, el método y el identificador, y la API devuelve `cobrado_por`. Docker conserva los logs de cada contenedor (el pipeline los archiva). | Anexo B, `azure-pipelines.yml` (`logs-servicios.txt`) |

### 7.6 Usuario y producción: uso seguro y pruebas de los controles

El uso seguro se explica en el manual (sección 6, "Buenas prácticas"). Los controles se comprobaron así:

| Control probado | Prueba | Resultado |
|---|---|---|
| Acceso sin token | S01 y CP-22 | 401 *Token requerido* |
| Token alterado | Anexo A y CP-22 | 401 *Token inválido* |
| Suscriptor consulta otro cliente | Anexo A y CP-23 | 403 |
| Suscriptor intenta cobrar | Anexo A, S04 y CP-23 | 403 en la API y bloqueo en el portal |
| Inyección SQL | Anexo A y CP-24 | 422, sin ejecutar SQL |
| Monto alterado | Anexo A | 422 |
| Cobro duplicado | Anexo A y prueba de sistema | 409 |
| Contraseña débil / cambio sin contraseña actual | Anexo A, CP-36 a CP-38 | 422 / 401 |

![API sin token](evidencias/capturas/S01_api_sin_token_401.png)

![Suscriptor bloqueado en el portal](evidencias/capturas/S04_suscriptor_bloqueado_en_portal.png)

### 7.7 Hallazgos y plan de mejora (autoevaluación)

| ID | Hallazgo | Riesgo | Acción |
|---|---|---|---|
| H1 | `jwt_secret()` tiene un valor por defecto de desarrollo si falta `JWT_SECRET` | Alto si se despliega sin la variable | Hacer que el servicio no arranque si falta (en Azure ya se inyecta un secreto aleatorio) |
| H2 | Un único usuario de base de datos con privilegios de administrador para los cuatro servicios | Medio | Un rol de PostgreSQL por esquema con `GRANT` mínimos |
| H3 | No hay límite de intentos de login ni revocación de JWT tras cambiar la contraseña | Medio | Rate limiting y una lista de revocación o `token_version` |
| H4 | La auditoría registra el usuario de base de datos (`postgres`), no el usuario de la aplicación. No hay prueba de restauración de respaldos. | Medio | Pasar el usuario con `SET LOCAL app.usuario` y leerlo en el trigger. Probar el *restore*. |
| H5 | El pipeline no escanea vulnerabilidades. El ACR usa usuario administrador. Los cuatro servicios tienen ingreso externo. | Medio | Agregar `pip-audit` y Trivy, usar identidad administrada y dejar solo ms_pagos y ms_auth con ingreso público |
| H6 | Los valores de demostración de `.env.example` (`admin123`) | Bajo (solo local) | Reemplazarlos al crear `.env` en cualquier ambiente compartido |

---

## 8. Resultados

### Beneficios comprobados en el sistema

| Antes (manual) | Con la solución | Evidencia |
|---|---|---|
| El pago se registraba después, en oficina | Se registra en el momento del cobro | M04, tabla `pagos` |
| Transcripción de monto y factura | El monto lo valida el sistema contra la factura (422 si no coincide) | Anexo A |
| Riesgo de cobrar dos veces | Bloqueo de fila más validación de estado (409) | Anexo A |
| Sin comprobante inmediato | Recibo único `FC-…` generado con `secrets` | M04 |
| Conciliación manual | Cierre diario automático por método de pago | `vw_cierre_diario_pagos` |
| Sin rastro de cambios de servicio | Auditoría automática por trigger | Anexo B |

### Aporte a la transformación digital

- **Digitaliza un proceso de ingreso:** el cobro pasa del papel a una transacción validada y trazable.
- **Datos confiables para decidir:** el estado de las facturas y la recaudación diaria están disponibles al instante.
- **Base para escalar:** al usar microservicios, contenedores y CI/CD, se pueden agregar más procesos (soporte, inventario de red) sin rehacer la plataforma.
- **Seguridad desde el diseño:** las pruebas de seguridad forman parte del pipeline y se ejecutan en cada cambio.

---

## 9. Conclusiones y anexos

### Conclusiones

1. El cobro en campo quedó automatizado de punta a punta dentro del sistema: autenticación, consulta, validación, registro, cambio de estado y recibo. Funciona sobre contenedores con los cuatro servicios sanos.
2. La seguridad se incorporó en todas las capas: API (JWT, roles, validación), base de datos (restricciones, triggers, consultas parametrizadas), contenedores (usuario sin privilegios) y pipeline (secretos, pruebas automáticas). Además se comprobó con 58 pruebas aprobadas y con ataques de prueba documentados.
3. La prueba de carga concurrente (CP-26) no cumplió la meta de p95, aunque no hubo errores. Antes de producción hay que ajustar `DB_POOL_MAX_SIZE` y las réplicas y repetir la prueba en el ambiente de Azure.
4. Quedan pendientes, documentados en 7.7: secreto JWT obligatorio, mínimo privilegio en la base de datos, límite de intentos de login, respaldo probado y escaneo de dependencias. Además, la reconexión física de la ONU y la integración con SAT y con la pasarela bancaria siguen como trabajo futuro: hoy el trigger marca la factura como pagada, pero no actúa sobre la OLT.

### Anexo A. Respuestas reales de la API ante intentos indebidos

```
GET /api/facturas sin token                         -> HTTP 401 {"detail":"Token requerido"}
GET /api/facturas con token manipulado              -> HTTP 401 {"detail":"Token inválido"}
Suscriptor (cliente 1) consulta facturas cliente 2  -> HTTP 403 {"detail":"Solo puede consultar sus propias facturas"}
Suscriptor intenta POST /api/pagos                  -> HTTP 403 {"detail":"Rol sin permiso para esta operación"}
Técnico cobra Q1.00 a factura de Q299.00            -> HTTP 422 {"detail":"El monto Q1.00 no coincide con el total de la factura Q299.00"}
Técnico usa método "Bitcoin"                        -> HTTP 422 {"detail":"Método de pago no permitido"}
Técnico cobra otra vez la factura 2 (ya pagada)     -> HTTP 409 {"detail":"La factura ya está en estado Pagado"}
Inyección SQL id_cliente="1 OR 1=1"                 -> HTTP 422 int_parsing (no llega a la base de datos)
Login con contraseña incorrecta                     -> HTTP 401 {"detail":"Credenciales inválidas"}
Registro con contraseña "12345"                     -> HTTP 422 {"detail":"La contraseña no cumple la política (...)"}
Cambio de estado a "Borrado"                        -> HTTP 422 {"detail":"Estado no válido"}
```

### Anexo B. Evidencia en la base de datos

```
-- Contraseñas almacenadas como hash bcrypt (se muestra solo el prefijo)
            correo            |    rol     | hash_bcrypt
 hazel.perez@fivercable.com   | Suscriptor | $2b$10$…
 juan.lopez@gmail.com         | Suscriptor | $2b$10$…
 tecnico.campo@fivercable.com | Tecnico    | $2b$10$…

-- Auditoría generada por trg_auditar_cliente tras PATCH /api/clientes/2/estado
 id | id_cliente |         accion         | usuario_operador |    fecha_evento     | detalles
  1 |          2 | CAMBIO_ESTADO_SERVICIO | postgres         | 2026-10-10 12:04:38 | {"estado_nuevo": "Moroso", "estado_anterior": "Activo"}
  2 |          2 | CAMBIO_ESTADO_SERVICIO | postgres         | 2026-10-10 12:04:38 | {"estado_nuevo": "Activo", "estado_anterior": "Moroso"}
```

### Anexo C. Archivos de evidencia

| Archivo | Contenido |
|---|---|
| [evidencias/capturas/](evidencias/capturas/) | Capturas del portal integrado y de la API (E = entorno, M = manual, S = seguridad) |
| [evidencias/capturas-prototipo/](evidencias/capturas-prototipo/) | Capturas automáticas de Selenium del prototipo (CP-29 a CP-39) |
| [evidencias/reporte-pruebas.html](evidencias/reporte-pruebas.html) | Reporte de Pytest de la ejecución completa |
| [evidencias/capturar_evidencias.py](evidencias/capturar_evidencias.py) | Script que regenera las capturas del portal |

Para regenerar las evidencias:

```powershell
docker compose down -v; docker compose up -d --build --wait
python docs/evidencias/capturar_evidencias.py
```

> Nota del entorno: si en Windows hay un PostgreSQL local escuchando en el puerto 5432, las pruebas de integración se conectan a ese servidor en lugar del contenedor. En ese caso, exponga el contenedor en otro puerto y ejecute las pruebas con `DB_PORT` apuntando a ese puerto.

---

## 10. Guion de la exposición (10 minutos)

| Tiempo | Contenido | Quién | Qué mostrar |
|---|---|---|---|
| 0:00–1:00 | Fiver Cable y el proceso de cobro en campo | Integrante 1 | Sección 1 |
| 1:00–2:00 | El problema: cobro manual, atraso, errores, cobro duplicado | Integrante 1 | Tabla "Antes / Con la solución" |
| 2:00–3:00 | Solución, arquitectura y tecnologías | Integrante 2 | Diagrama de arquitectura |
| 3:00–6:00 | **Demostración en vivo:** `docker compose ps` → login → buscar cliente 2 → intento con tarjeta sin autorización (rechazo) → cobro en efectivo → recibo → buscar de nuevo | Integrante 2 | Portal en `:3003/portal` |
| 6:00–8:00 | Controles de seguridad: API sin token (401), suscriptor (403), monto alterado (422), duplicado (409), auditoría en BD, secretos en el pipeline | Integrante 3 | Anexo A, matriz de roles, límites de confianza |
| 8:00–9:00 | Pruebas y CI/CD: 58/59, CP-26 y su plan, pipeline Build → Test → Deploy | Integrante 3 | Reporte HTML, `azure-pipelines.yml` |
| 9:00–10:00 | Resultados, beneficios, pendientes y cierre | Integrante 1 | Secciones 8 y 9 |

Recomendaciones para la exposición:

- Levantar el ambiente 10 minutos antes y reiniciar los datos con `docker compose down -v; docker compose up -d --wait`, para que las facturas de demostración estén pendientes.
- Tener abiertas las capturas de `docs/evidencias/capturas` como respaldo si falla la demostración en vivo.
- No mostrar el archivo `.env` ni escribir contraseñas a la vista. Usar el gestor de contraseñas del navegador o escribirlas con la pantalla compartida pausada.
- Si se presenta Azure, mostrar solo las URL públicas y el run del pipeline, nunca la página de variables o secretos.
