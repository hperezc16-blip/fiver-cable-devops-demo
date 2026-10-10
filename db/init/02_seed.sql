-- ============================================================================
-- DATOS DE PRUEBA (POBLAMIENTO INICIAL) - SOLO ENTORNOS DE DESARROLLO / STAGING
-- Contraseñas de prueba (NO productivas), documentadas en .env.example:
--   tecnico.campo@fivercable.com  -> TEST_TECNICO_PASSWORD
--   hazel.perez@fivercable.com    -> TEST_SUSCRIPTOR_PASSWORD
-- ============================================================================

INSERT INTO red_db.planes_servicio (nombre_plan, megas_bajada, megas_subida, precio_mensual, descripcion)
VALUES
('Básico Hogar', 25, 10, 199.00, '25 Mbps Fibra Óptica + TV Básica'),
('Estándar Familiar', 50, 20, 299.00, '50 Mbps Fibra Óptica + TV Digital'),
('Premium Corporativo', 100, 50, 499.00, '100 Mbps Simétricos + IPTV HD');

INSERT INTO usuarios_db.clientes (id_plan_ref, dpi_nit, nombres, apellidos, direccion_instalacion, telefono, correo, password_hash, rol)
VALUES
(2, '1234567890101', 'Hazel Ruvi', 'Perez Carcamo', 'Zona 10, Ciudad de Guatemala', '55551234', 'hazel.perez@fivercable.com',
 '$2b$10$n.e5uX4UcTIwWLaghfk6I.qcd.a2E8r1/y9Ibo/t/9InZI8qZGrbO', 'Suscriptor'),
(3, '9876543210101', 'Juan Carlos', 'Lopez Gomez', 'Zona 1, Guatemala', '55559876', 'juan.lopez@gmail.com',
 '$2b$10$n.e5uX4UcTIwWLaghfk6I.qcd.a2E8r1/y9Ibo/t/9InZI8qZGrbO', 'Suscriptor'),
(1, 'CF', 'Técnico', 'de Campo', 'Oficina central Fiver Cable', '55550000', 'tecnico.campo@fivercable.com',
 '$2b$10$9b.PuNE8iDfTPI4zt9eQAO7Wb7UEo6ZYyCTsmbcZKyGwDlaNZMVc2', 'Tecnico');

INSERT INTO red_db.dispositivos_onu (id_cliente_ref, mac_address, serial_number, ip_asignada, puerto_olt, potencia_optica_dbm, estado_conexion)
VALUES
(1, '48:57:DD:A1:B2:C3', 'HWTC12345678', '10.20.5.14', 'Slot1/Pon3', -19.50, 'Online'),
(2, '48:57:DD:F4:E5:D6', 'HWTC87654321', '10.20.5.15', 'Slot1/Pon1', -28.20, 'Corta_Velocidad');

INSERT INTO billing_db.facturas_fel (id_cliente_ref, uuid_sat, serie_fel, numero_fel, monto_total, estado_pago)
VALUES
(1, 'A1B2C3D4-0001-4F00-9A00-000000000001', 'FEL-A', '1001', 299.00, 'Pendiente'),
(2, 'A1B2C3D4-0002-4F00-9A00-000000000002', 'FEL-A', '1002', 499.00, 'Pendiente'),
(2, 'A1B2C3D4-0003-4F00-9A00-000000000003', 'FEL-A', '1003', 499.00, 'Pendiente');

INSERT INTO soporte_db.tickets_soporte (id_cliente_ref, tipo_incidencia, descripcion_falla, prioridad)
VALUES
(2, 'Señal baja', 'ONU reporta potencia -28.20 dBm, navegación lenta', 'Alta');

-- ============================================================================
-- PERSONAL Y DATOS ADICIONALES PARA LA APLICACIÓN WEB (entrega final)
-- Contraseñas de prueba documentadas en .env.example (TEST_ADMIN_*, TEST_JEFATURA_*,
-- TEST_SECRETARIA_*). Los clientes nuevos usan la misma contraseña de suscriptor de prueba.
-- Se agregan al final para no alterar los identificadores usados por las pruebas.
-- ============================================================================
INSERT INTO usuarios_db.clientes (id_plan_ref, dpi_nit, nombres, apellidos, direccion_instalacion, telefono, correo, password_hash, rol)
VALUES
(1, 'CF', 'Administración', 'Fiver Cable', 'Oficina central Fiver Cable', '55550001', 'admin@fivercable.com',
 '$2b$10$uv7X88IQBqTJ5snWZ5YtGewsxx8C8U4Bpm673lCu/u7Aag4/95Y1y', 'Administrador'),
(1, 'CF', 'Jefatura', 'de Operaciones', 'Oficina central Fiver Cable', '55550002', 'jefatura@fivercable.com',
 '$2b$10$9kgqOQLr3K6PuMeWh0uvzOpWf6GB.D2LXJT2Zjcb.znnF45sN/bpK', 'Jefatura'),
(1, 'CF', 'Secretaría', 'de Oficina', 'Oficina central Fiver Cable', '55550003', 'secretaria@fivercable.com',
 '$2b$10$HzqczyllYHSeev.OHiT2g.dkTWWaD/LJz3OC0JMKB0RaA0zu6Bkt.', 'Secretaria');

INSERT INTO usuarios_db.clientes (id_plan_ref, dpi_nit, nombres, apellidos, direccion_instalacion, telefono, correo, password_hash, rol, estado_servicio)
VALUES
(2, '2345678901201', 'María José', 'Ramírez Ortiz', '12 avenida 4-25, zona 11, Guatemala', '55553011', 'maria.ramirez@correo.gt',
 '$2b$10$n.e5uX4UcTIwWLaghfk6I.qcd.a2E8r1/y9Ibo/t/9InZI8qZGrbO', 'Suscriptor', 'Moroso'),
(1, '3456789012301', 'Carlos Eduardo', 'Méndez Pérez', '7a calle 9-18, zona 7, Guatemala', '55553022', 'carlos.mendez@correo.gt',
 '$2b$10$n.e5uX4UcTIwWLaghfk6I.qcd.a2E8r1/y9Ibo/t/9InZI8qZGrbO', 'Suscriptor', 'Activo'),
(3, '4567890123401', 'Ana Lucía', 'García Soto', '3a avenida 12-40, zona 12, Mixco', '55553033', 'ana.garcia@correo.gt',
 '$2b$10$n.e5uX4UcTIwWLaghfk6I.qcd.a2E8r1/y9Ibo/t/9InZI8qZGrbO', 'Suscriptor', 'Suspendido'),
(2, '5678901234501', 'Jorge Luis', 'Castillo Rivas', 'Calzada Roosevelt 22-10, zona 7', '55553044', 'jorge.castillo@correo.gt',
 '$2b$10$n.e5uX4UcTIwWLaghfk6I.qcd.a2E8r1/y9Ibo/t/9InZI8qZGrbO', 'Suscriptor', 'Activo');

INSERT INTO red_db.dispositivos_onu (id_cliente_ref, mac_address, serial_number, ip_asignada, puerto_olt, potencia_optica_dbm, estado_conexion)
VALUES
(7, '48:57:DD:10:20:31', 'HWTC20000031', '10.20.6.21', 'Slot2/Pon1', -21.30, 'Corta_Velocidad'),
(8, '48:57:DD:10:20:42', 'HWTC20000042', '10.20.6.22', 'Slot2/Pon2', -18.75, 'Online'),
(9, '48:57:DD:10:20:53', 'HWTC20000053', '10.20.6.23', 'Slot2/Pon3', -29.10, 'Suspendido'),
(10, '48:57:DD:10:20:64', 'HWTC20000064', '10.20.6.24', 'Slot3/Pon1', -7.40, 'Online');

INSERT INTO billing_db.facturas_fel (id_cliente_ref, uuid_sat, serie_fel, numero_fel, fecha_emision, monto_total, estado_pago)
VALUES
(7, 'A1B2C3D4-0004-4F00-9A00-000000000004', 'FEL-A', '1004', CURRENT_DATE - 40, 299.00, 'Pendiente'),
(7, 'A1B2C3D4-0005-4F00-9A00-000000000005', 'FEL-A', '1005', CURRENT_DATE - 10, 299.00, 'Pendiente'),
(8, 'A1B2C3D4-0006-4F00-9A00-000000000006', 'FEL-A', '1006', CURRENT_DATE - 12, 199.00, 'Pendiente'),
(9, 'A1B2C3D4-0007-4F00-9A00-000000000007', 'FEL-A', '1007', CURRENT_DATE - 45, 499.00, 'Pendiente'),
(10, 'A1B2C3D4-0008-4F00-9A00-000000000008', 'FEL-A', '1008', CURRENT_DATE - 9, 299.00, 'Pendiente'),
(8, 'A1B2C3D4-0009-4F00-9A00-000000000009', 'FEL-A', '0990', CURRENT_DATE - 42, 199.00, 'Pendiente'),
(10, 'A1B2C3D4-0010-4F00-9A00-000000000010', 'FEL-A', '0991', CURRENT_DATE - 39, 299.00, 'Pendiente'),
(1, 'A1B2C3D4-0011-4F00-9A00-000000000011', 'FEL-A', '0992', CURRENT_DATE - 38, 299.00, 'Pendiente');

-- Historial de cobros (el trigger marca cada factura como Pagado)
INSERT INTO billing_db.pagos (id_factura, id_transaccion_pasarela, monto_pagado, fecha_pago, metodo_pago, codigo_autorizacion, registrado_por)
VALUES
(9, 'FC-HIST-0001', 199.00, CURRENT_DATE - 2 + TIME '09:15', 'Efectivo', NULL, 'tecnico.campo@fivercable.com'),
(10, 'FC-HIST-0002', 299.00, CURRENT_DATE - 1 + TIME '11:40', 'Tarjeta', 'AUT-552190', 'secretaria@fivercable.com'),
(11, 'FC-HIST-0003', 299.00, CURRENT_DATE - 1 + TIME '15:05', 'Transferencia', 'TRF-889120', 'tecnico.campo@fivercable.com');

INSERT INTO soporte_db.tickets_soporte (id_cliente_ref, tipo_incidencia, descripcion_falla, prioridad, estado_ticket)
VALUES
(9, 'Sin servicio', 'Cliente reporta corte total desde ayer por la noche', 'Critica', 'Abierto'),
(7, 'Velocidad', 'Navegación lenta e intermitente por la tarde', 'Alta', 'En_Proceso'),
(8, 'Consulta', 'Solicita información para cambio de plan', 'Baja', 'Abierto');
