# ETL CB1 / B1 — Emisión DTE 33, 39 y 61

ETL versionado para generar y, sólo con confirmación explícita, emitir documentos mediante OnlineGenerationDte:

- `33`: factura electrónica B1.
- `39`: boleta electrónica B1.
- `61`: nota de crédito CB1.

El motor se selecciona por `RUT_EMISOR`: ACEPTA o Cóndor/Paperless.

**Versión actual:** `2.0.0`

## Archivos locales en la raíz

Después de instalar, la raíz debe contener:

```text
cb1-b1\
├─ reporte_diario.csv
├─ config_dte_onlinegeneration.ini
├─ src\
├─ scripts\
├─ instalacion\
├─ examples\
└─ tests\
```

`reporte_diario.csv` y `config_dte_onlinegeneration.ini` quedan sólo en tu equipo y están excluidos de GitHub.

## Contrato de entrada

El contrato no es retrocompatible. `TIPO_DOC` representa siempre el DTE que se emitirá. Para una NC se deben informar además `TIPO_DOC_REF`, `FOLIO_REBAJADO`, `EMISION_BOLETA` y `MONTO_NCRD`.

La antigüedad máxima del documento referenciado se configura en:

```ini
[REGLAS]
meses_documento_referencia_nc = 1
```

`1` permite el mes de ejecución y el mes inmediatamente anterior. La validación se realiza por mes calendario.

## Inicio rápido en Windows

```bat
instalacion\instalar_windows.cmd
scripts\probar_codigo.cmd
scripts\ejecutar_prueba.cmd reporte_diario.csv
```

La prueba es un dry-run: genera los archivos de control y no llama al servicio de emisión.

Para una emisión real limitada a dos documentos:

```bat
scripts\ejecutar_real.cmd reporte_diario.csv
```

La emisión real exige escribir `EMITIR`.

## Advertencia de homologación

La generación NC conserva el layout previamente validado. La generación B1 `33/39` usa registros `E/D/G/T` y debe homologarse mediante dry-run y pruebas controladas con cada facturador antes de una emisión masiva.

Consulta [`instalacion/INSTALACION_Y_USO.md`](instalacion/INSTALACION_Y_USO.md) para el contrato completo del CSV y ejemplos.
