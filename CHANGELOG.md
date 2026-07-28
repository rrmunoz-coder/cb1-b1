# Historial de versiones

## 1.1.0 — 2026-07-28

- Revisión técnica y empaquetado inicial en GitHub.
- Corrección de `parse_int`: valores Excel como `39.0` ya no se transforman erróneamente en `390`.
- Corrección de `parse_monto`: montos chilenos como `23.000` se interpretan como `23000`.
- Nuevo parámetro explícito `--procesar-todos`; se conserva `--permitir-mas-de-max` por compatibilidad.
- Se ocultan login y hash en el SOAP de previsualización.
- Se agrega versión, nombre y SHA-256 del archivo de entrada al CSV de control.
- Se agrega resumen OK/NOK al log.
- Se elimina el endpoint interno predeterminado del código público; debe configurarse en el INI local.
- Se incorporan pruebas automáticas, scripts Windows, documentación y plantilla de configuración.

## 1.0.0 — versión recibida

- Emisión NC DTE 61 por OnlineGenerationDte.
- Ruteo ACEPTA / Cóndor-Paperless según RUT emisor.
- Construcción posicional E/D/F/G/T.
- Modo seguro dry-run y salida única de control.
