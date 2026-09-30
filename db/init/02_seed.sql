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
