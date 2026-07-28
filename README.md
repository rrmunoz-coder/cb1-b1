# ETL CB1 / B1 — Emisión DTE 33, 39 y 61

ETL versionado para generar y, sólo con confirmación explícita, emitir documentos mediante OnlineGenerationDte:

- `33`: factura electrónica B1.
- `39`: boleta electrónica B1.
- `61`: nota de crédito CB1.

El motor se selecciona por `RUT_EMISOR`: ACEPTA o Cóndor/Paperless.

**Versión actual:** `2.0.0`

## Cambio principal de la versión 2

El contrato de entrada no es retrocompatible. `TIPO_DOC` representa siempre el DTE que se emitirá. Para una NC se deben informar además `TIPO_DOC_REF`, `FOLIO_REBAJADO`, `EMISION_BOLETA` y `MONTO_NCRD`.

La antigüedad máxima del documento referenciado se configura en el INI:

```ini
[REGLAS]
meses_documento_referencia_nc = 1
```

`1` permite el mes de ejecución y el mes inmediatamente anterior. La validación se realiza por mes calendario.

## Seguridad

El repositorio es público. No contiene configuración real, CSV operacionales, respuestas del facturador ni datos personales. Estos archivos están excluidos mediante `.gitignore`.

## Inicio rápido en Windows

```bat
instalacion\instalar_windows.cmd
scripts\probar_codigo.cmd
scripts\ejecutar_prueba.cmd
```

Luego completa `config_nc_onlinegeneration.ini` sólo en tu equipo. Para una emisión real limitada a dos documentos:

```bat
scripts\ejecutar_real.cmd reporte_diario.csv
```

La emisión real exige escribir `EMITIR`.

## Advertencia de homologación

La generación NC conserva el layout previamente validado. La generación B1 `33/39` usa registros `E/D/G/T` y debe homologarse mediante dry-run y pruebas controladas con cada facturador antes de una emisión masiva.

Consulta [`instalacion/INSTALACION_Y_USO.md`](instalacion/INSTALACION_Y_USO.md) para el contrato completo del CSV y ejemplos.
