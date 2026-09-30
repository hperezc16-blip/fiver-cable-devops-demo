-- ============================================================================
-- SCRIPT DE IMPLEMENTACIÓN DE BASE DE DATOS - FIVER CABLE
-- Arquitectura: Database-per-Service / Multi-Schema PostgreSQL 16
-- Fuente: Entregable 8 (script ejecutado en pgAdmin 4). Se versiona aquí para
-- que el pipeline CI/CD cree la base de datos de forma automática y repetible.
-- ============================================================================

SET client_encoding = 'UTF8';
SET TIME ZONE 'America/Guatemala';  -- corregido en DevOps 2: 'SET time_zone' es sintaxis MySQL

-- ----------------------------------------------------------------------------
-- 1. CREACIÓN DE ESQUEMAS INDEPENDIENTES (MICROSERVICIOS)
--    usuarios_db -> ms_auth      red_db     -> ms_catalogo
--    billing_db  -> ms_pagos     soporte_db -> ms_pedidos
-- ----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS usuarios_db;
CREATE SCHEMA IF NOT EXISTS red_db;
CREATE SCHEMA IF NOT EXISTS billing_db;
CREATE SCHEMA IF NOT EXISTS soporte_db;

-- ============================================================================
-- ESQUEMA 1: usuarios_db (Servicio de Autenticación y Usuarios) -> ms_auth
-- ============================================================================
CREATE TABLE IF NOT EXISTS usuarios_db.clientes (
    id_cliente SERIAL PRIMARY KEY,
    id_plan_ref INT NOT NULL, -- Referencia lógica a red_db.planes_servicio
    dpi_nit VARCHAR(20) NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    direccion_instalacion TEXT NOT NULL,
    telefono VARCHAR(15) NOT NULL,
    correo VARCHAR(100) NOT NULL UNIQUE,
    estado_servicio VARCHAR(20) NOT NULL DEFAULT 'Activo'
        CHECK (estado_servicio IN ('Activo', 'Moroso', 'Suspendido', 'Inactivo')),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL DEFAULT 'Suscriptor'
        CHECK (rol IN ('Suscriptor', 'Tecnico', 'Administrador'))
);

CREATE TABLE IF NOT EXISTS usuarios_db.auditoria_usuarios (
    id_auditoria SERIAL PRIMARY KEY,
    id_cliente INT NOT NULL,
    accion VARCHAR(50) NOT NULL,
    usuario_operador VARCHAR(100) NOT NULL,
    fecha_evento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detalles JSONB
);

CREATE OR REPLACE VIEW usuarios_db.vw_suscriptores_activos AS
SELECT id_cliente, dpi_nit, nombres, apellidos, correo, telefono, estado_servicio, fecha_registro
FROM usuarios_db.clientes
WHERE estado_servicio = 'Activo';

CREATE OR REPLACE FUNCTION usuarios_db.fn_trg_auditar_cliente()
RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.estado_servicio IS DISTINCT FROM NEW.estado_servicio) THEN
        INSERT INTO usuarios_db.auditoria_usuarios (id_cliente, accion, usuario_operador, detalles)
        VALUES (
            NEW.id_cliente,
            'CAMBIO_ESTADO_SERVICIO',
            CURRENT_USER,
            jsonb_build_object('estado_anterior', OLD.estado_servicio, 'estado_nuevo', NEW.estado_servicio)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auditar_cliente ON usuarios_db.clientes;
CREATE TRIGGER trg_auditar_cliente
AFTER UPDATE ON usuarios_db.clientes
FOR EACH ROW EXECUTE FUNCTION usuarios_db.fn_trg_auditar_cliente();

-- ============================================================================
-- ESQUEMA 2: red_db (Servicio Agente OLT / Provisionamiento) -> ms_catalogo
-- ============================================================================
CREATE TABLE IF NOT EXISTS red_db.planes_servicio (
    id_plan SERIAL PRIMARY KEY,
    nombre_plan VARCHAR(50) NOT NULL,
    megas_bajada INT NOT NULL CHECK (megas_bajada > 0),
    megas_subida INT NOT NULL CHECK (megas_subida > 0),
    precio_mensual DECIMAL(10,2) NOT NULL CHECK (precio_mensual > 0),
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS red_db.dispositivos_onu (
    id_onu SERIAL PRIMARY KEY,
    id_cliente_ref INT NOT NULL, -- Referencia lógica a usuarios_db.clientes
    mac_address VARCHAR(17) NOT NULL UNIQUE,
    serial_number VARCHAR(50) NOT NULL,
    ip_asignada VARCHAR(15),
    puerto_olt VARCHAR(20) NOT NULL,
    potencia_optica_dbm DECIMAL(5,2),
    estado_conexion VARCHAR(20) NOT NULL DEFAULT 'Online'
        CHECK (estado_conexion IN ('Online', 'Offline', 'Corta_Velocidad', 'Suspendido'))
);

CREATE OR REPLACE VIEW red_db.vw_onus_senal_critica AS
SELECT id_onu, id_cliente_ref, mac_address, puerto_olt, potencia_optica_dbm, estado_conexion
FROM red_db.dispositivos_onu
WHERE potencia_optica_dbm < -27.00 OR potencia_optica_dbm > -8.00;

CREATE OR REPLACE PROCEDURE red_db.sp_actualizar_estado_onu(
    p_id_cliente INT,
    p_nuevo_estado VARCHAR
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE red_db.dispositivos_onu
    SET estado_conexion = p_nuevo_estado
    WHERE id_cliente_ref = p_id_cliente;

    RAISE NOTICE 'Estado OLT actualizado a % para el cliente ref %', p_nuevo_estado, p_id_cliente;
END;
$$;

-- ============================================================================
-- ESQUEMA 3: billing_db (Servicio de Billing y Pasarela de Pagos) -> ms_pagos
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_db.facturas_fel (
    id_factura SERIAL PRIMARY KEY,
    id_cliente_ref INT NOT NULL, -- Referencia lógica a usuarios_db.clientes
    uuid_sat VARCHAR(36) NOT NULL UNIQUE,
    serie_fel VARCHAR(20) NOT NULL,
    numero_fel VARCHAR(20) NOT NULL,
    fecha_emision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    monto_total DECIMAL(10,2) NOT NULL CHECK (monto_total >= 0),
    estado_pago VARCHAR(20) NOT NULL DEFAULT 'Pendiente'
        CHECK (estado_pago IN ('Pendiente', 'Pagado', 'Anulado'))
);

CREATE TABLE IF NOT EXISTS billing_db.pagos (
    id_pago SERIAL PRIMARY KEY,
    id_factura INT NOT NULL REFERENCES billing_db.facturas_fel(id_factura) ON DELETE RESTRICT,
    id_transaccion_pasarela VARCHAR(100) NOT NULL,
    monto_pagado DECIMAL(10,2) NOT NULL CHECK (monto_pagado > 0),
    fecha_pago TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metodo_pago VARCHAR(30) NOT NULL,
    codigo_autorizacion VARCHAR(50)
);

CREATE OR REPLACE VIEW billing_db.vw_cierre_diario_pagos AS
SELECT
    DATE(fecha_pago) AS fecha,
    metodo_pago,
    COUNT(id_pago) AS total_transacciones,
    SUM(monto_pagado) AS total_recaudado
FROM billing_db.pagos
GROUP BY DATE(fecha_pago), metodo_pago;

CREATE OR REPLACE FUNCTION billing_db.fn_trg_procesar_pago_exitoso()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE billing_db.facturas_fel
    SET estado_pago = 'Pagado'
    WHERE id_factura = NEW.id_factura;

    RAISE NOTICE 'Evento Emitido: Factura % Pagada. Cliente REF % reconectado.',
        NEW.id_factura, (SELECT id_cliente_ref FROM billing_db.facturas_fel WHERE id_factura = NEW.id_factura);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_procesar_pago_exitoso ON billing_db.pagos;
CREATE TRIGGER trg_procesar_pago_exitoso
AFTER INSERT ON billing_db.pagos
FOR EACH ROW EXECUTE FUNCTION billing_db.fn_trg_procesar_pago_exitoso();

-- ============================================================================
-- ESQUEMA 4: soporte_db (Servicio de Tickets y Soporte) -> ms_pedidos
-- ============================================================================
CREATE TABLE IF NOT EXISTS soporte_db.tickets_soporte (
    id_ticket SERIAL PRIMARY KEY,
    id_cliente_ref INT NOT NULL, -- Referencia lógica a usuarios_db.clientes
    id_tecnico_asignado INT,
    tipo_incidencia VARCHAR(50) NOT NULL,
    descripcion_falla TEXT NOT NULL,
    prioridad VARCHAR(20) NOT NULL DEFAULT 'Media'
        CHECK (prioridad IN ('Baja', 'Media', 'Alta', 'Critica')),
    estado_ticket VARCHAR(20) NOT NULL DEFAULT 'Abierto'
        CHECK (estado_ticket IN ('Abierto', 'En_Proceso', 'Resuelto', 'Cerrado')),
    fecha_apertura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP
);

CREATE OR REPLACE VIEW soporte_db.vw_tickets_pendientes AS
SELECT id_ticket, id_cliente_ref, tipo_incidencia, prioridad, estado_ticket, fecha_apertura
FROM soporte_db.tickets_soporte
WHERE estado_ticket IN ('Abierto', 'En_Proceso');

CREATE OR REPLACE PROCEDURE soporte_db.sp_cerrar_ticket(
    p_id_ticket INT,
    p_tecnico_id INT
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE soporte_db.tickets_soporte
    SET estado_ticket = 'Cerrado',
        id_tecnico_asignado = p_tecnico_id,
        fecha_cierre = CURRENT_TIMESTAMP
    WHERE id_ticket = p_id_ticket;

    RAISE NOTICE 'Ticket % cerrado exitosamente por técnico %', p_id_ticket, p_tecnico_id;
END;
$$;
