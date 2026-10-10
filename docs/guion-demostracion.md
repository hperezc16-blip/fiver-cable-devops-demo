# Guion de demostración de la aplicación

Este guion sirve para la demostración en vivo y para grabar el video del equipo. La aplicación es el **portal web de operaciones** de Fiver Cable, conectado a las cuatro APIs y a PostgreSQL.

| Aplicación | Dirección | Qué demuestra |
|---|---|---|
| Portal web (5 roles) | `http://localhost:3003/portal` | Proceso de cobro automatizado y operación de la empresa |
| APIs (OpenAPI) | `http://localhost:3000/docs` a `:3003/docs` | Servicios, endpoints y estado |
| Prototipo inicial | `prototipo/index.html` | Diseño original del equipo (datos simulados) |

## Cuentas de demostración

Son las cuentas de `.env.example` (variables `TEST_*`), solo para el ambiente de demostración. Escriba las contraseñas sin mostrarlas en pantalla.

| Rol | Correo | Para mostrar |
|---|---|---|
| Técnico | `tecnico.campo@fivercable.com` | Cobro en campo, reactivación, tickets, red |
| Secretaría | `secretaria@fivercable.com` | Registro de clientes, facturación, pago en oficina |
| Jefatura | `jefatura@fivercable.com` | Panel de indicadores, cierre diario, auditoría |
| Administrador | `admin@fivercable.com` | Todo, más alta de personal |
| Cliente | `maria.ramirez@correo.gt` o `hazel.perez@fivercable.com` | Su cuenta, facturas y reporte de fallas |

Datos útiles: el **cliente 7** (María José Ramírez) está *Moroso* con 2 facturas pendientes; el **cliente 9** (Ana Lucía García) está *Suspendido*; el **cliente 2** tiene 2 facturas de Q 499.00.

---

## Preparación (10 minutos antes)

1. Abrir **Docker Desktop** y esperar a que diga *Engine running*.
2. En la terminal de VS Code, dentro de la carpeta del proyecto, reiniciar los datos de demostración:
   ```powershell
   docker compose down -v
   docker compose up -d --build --wait
   docker compose ps
   ```
   Los seis contenedores deben aparecer como `healthy` o `Up`.
3. Abrir `http://localhost:3003/portal` en el navegador.
4. Tener a mano las capturas de `docs/evidencias/capturas` por si algo falla.
5. Cerrar el archivo `.env` y cualquier ventana que muestre contraseñas.
6. Subir el zoom del navegador a 110–125 % para que se lea desde el fondo del salón.

---

## Demo principal (3 minutos): el proceso de cobro automatizado

| # | Acción | Qué decir |
|---|---|---|
| 1 | Terminal: `docker compose ps` | "La aplicación corre en contenedores: PostgreSQL y cuatro microservicios, todos sanos." |
| 2 | Login con contraseña incorrecta | "Si la contraseña es incorrecta no entra, y el mensaje no revela si el correo existe." |
| 3 | Login como **Técnico** | "Cada rol ve su propio menú. Este es el panel del técnico con los indicadores del día." |
| 4 | **Cobro en campo** → cliente `7`, método **Tarjeta**, sin autorización → **Buscar facturas** | "Vemos la ficha del cliente: está Moroso y tiene dos facturas pendientes." |
| 5 | **Cobrar** | "Con tarjeta, la API exige el código de autorización y rechaza el cobro." |
| 6 | Cambiar a **Efectivo** → **Cobrar** las dos facturas | "Cobro registrado: factura Pagada y recibo único FC-…, que se puede imprimir." |
| 7 | **Reactivar servicio** | "Sin saldo pendiente, el técnico reactiva el servicio en el momento, sin pasar por oficina. Ese es el problema que resolvimos." |
| 8 | **Cerrar sesión** → login como **Jefatura** | "Jefatura ve el impacto al instante: lo recaudado hoy subió y el cierre diario se calcula solo." |
| 9 | **Auditoría** | "Cada cambio de estado queda registrado con el usuario que lo hizo, y no se puede editar." |
| 10 | Abrir `http://localhost:3003/api/facturas?id_cliente=1` | "Sin token, la API responde 401. Nadie consulta datos sin autenticarse." |

## Demos adicionales (si hay tiempo, 1 minuto cada una)

**Secretaría (oficina):**
1. **Clientes** → **Registrar suscriptor** → llenar el formulario → **Registrar**. El sistema asigna el código.
2. Desde la ficha, **Emitir factura** → elegir el plan → **Emitir factura FEL**.
3. **Pago en oficina** → cobrar con **Tarjeta** y un código de autorización (por ejemplo `AUT-1234`).

**Cliente (en celular):**
1. En Chrome presione `F12` y luego `Ctrl + Shift + M` para ver la página en tamaño celular.
2. Login con la cuenta de cliente → ver saldo, plan y equipo.
3. **Soporte técnico** → describir la falla → **Enviar reporte**. Muestra la prioridad y el tiempo de atención.
4. Abrir el menú con el botón ☰.

**Administrador:** **Personal** → crear una cuenta de técnico; **Red y equipos** → ver la señal crítica de los equipos.

**Seguridad por rol:** con la cuenta de Jefatura, abrir un cliente en **Clientes**: no aparecen botones para cobrar ni cambiar estado. Aunque se llamara a la API directamente, respondería 403.

---

## Plan B

| Problema | Qué hacer |
|---|---|
| Docker no arranca o el portal no carga | Explicar el flujo con las capturas de `docs/evidencias/capturas` (M03, S03, M04, M05) |
| Ya no hay facturas pendientes (se cobraron en un ensayo) | `docker compose down -v` y `docker compose up -d --wait` (tarda unos 30 s) |
| "No se pudo conectar con el servicio" | Verificar con `docker compose ps` que los cuatro servicios estén arriba; si falta uno, `docker compose up -d` |
| Se acaba el tiempo | Saltar las demos adicionales y pasar a la diapositiva de seguridad |

## Regenerar las capturas de evidencia

```powershell
docker compose down -v; docker compose up -d --wait
python docs/evidencias/capturar_evidencias.py
```
