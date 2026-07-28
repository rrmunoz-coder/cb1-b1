# Historial de versiones

## 2.0.0 — 2026-07-28

Cambio mayor y no retrocompatible.

- Se habilita emisión mixta B1/CB1: DTE `33`, `39` y `61`.
- `TIPO_DOC` pasa a representar exclusivamente el DTE que se emitirá.
- Para NC se incorpora `TIPO_DOC_REF` como campo independiente.
- Se elimina `TIPO_DOC_TRIB` y toda lógica de compatibilidad con el contrato anterior.
- Para B1, `MONTO_DOC` es el total emitido.
- Para NC, `MONTO_NCRD` es el total emitido y `MONTO_DOC` corresponde al documento original.
- Las facturas DTE 33 exigen `GIRO` del receptor.
- Se agrega `[REGLAS] meses_documento_referencia_nc` al INI.
- Con valor `1`, la NC sólo acepta documentos del mes de ejecución o del mes anterior.
- Se rechazan referencias de meses futuros o con antigüedad superior al parámetro.
- B1 genera registros `E/D/G/T`; NC genera `E/D/F/G/T`.
- Se generalizan salida y nombres internos: `FOLIO_DTE`, `FECHA_DTE`, `MONTO_TOTAL_DTE`.
- Nuevo ejecutable: `src/etl_emision_dte_onlinegeneration_real.py`.
- Se agregan nueve pruebas automáticas para B1, NC, regla mensual, layouts, números y SOAP.

### Extracción Oracle incorporada

- Se agrega conexión directa a Oracle mediante `python-oracledb`.
- Fuente: `SCBILL.HP_CONSOLIDADO_ANDES_VTR_B1`.
- Se agrega `sql/candidatos_entrada_etl.sql` con filtros configurables.
- La consulta devuelve las 18 columnas exactas del contrato CSV.
- Se agrega cruce CB1 entre `FOLIO_REBAJADO` e `ID_DOC_PPL` para recuperar el documento original.
- Se agregan valores descriptivos de respaldo en `[ENTRADA_DEFAULTS]`.
- Los datos financieros o tributarios faltantes nunca se reemplazan por defaults.
- Los candidatos incompletos se separan en `salida_extraccion/candidatos_rechazados.csv`.
- Se agregan `scripts/extraer_oracle.cmd` y `scripts/extraer_y_probar.cmd`.
- Se agregan siete pruebas unitarias para el extractor.

### Riesgo residual

El layout B1 33/39 requiere homologación controlada con ACEPTA y Cóndor/Paperless antes de una corrida productiva masiva.

El cruce `FOLIO_REBAJADO = ID_DOC_PPL` debe validarse con casos reales antes de habilitar emisión masiva de CB1.

## 1.1.0 — 2026-07-28

- Revisión técnica y empaquetado inicial.
- Corrección de enteros Excel y montos chilenos.
- Seguridad de dry-run, SHA-256 de entrada, pruebas y documentación.

## 1.0.0 — versión recibida

- Emisión NC DTE 61 por OnlineGenerationDte.
