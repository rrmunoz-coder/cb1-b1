# Prompt maestro para regenerar o evolucionar el ETL

Usa este prompt junto con la última versión del código, el changelog, el manual y ejemplos sin datos reales.

---

Actúa como desarrollador senior Python especializado en ETL financiero, DTE chilenos, SOAP y controles auditables. Regenera o mejora el proyecto **ETL CB1/B1 — emisión DTE 33, 39 y 61 por OnlineGenerationDte**.

## Contrato funcional obligatorio

1. `TIPO_DOC` representa siempre el DTE a emitir: `33`, `39` o `61`.
2. No implementar compatibilidad con esquemas antiguos ni usar `TIPO_DOC_TRIB`.
3. Para B1 `33/39`, `MONTO_DOC` es el total emitido.
4. Para factura `33`, exigir `GIRO` del receptor.
5. Para NC `61`, exigir `TIPO_DOC_REF`, `FOLIO_REBAJADO`, `EMISION_BOLETA` y `MONTO_NCRD`.
6. Para NC, `MONTO_DOC` es el total original y `MONTO_NCRD` el total emitido.
7. `COD_REF=1` si ambos montos son iguales; de lo contrario `COD_REF=3`.
8. Rechazar `MONTO_NCRD > MONTO_DOC`.
9. Validar la fecha referenciada por mes calendario con `[REGLAS] meses_documento_referencia_nc`.
10. Con valor `1`, aceptar sólo el mes de ejecución y el mes anterior; rechazar meses futuros.
11. Enrutar `94675000-K` a ACEPTA y `76114143-0` a Cóndor/Paperless.

## Layouts

- DTE 33/39: E/D/G/T con largos 1405/2075/123/70.
- DTE 61: E/D/F/G/T con largos 1405/2075/185/123/70.
- En F conservar `FchRef` 35–42 y `CodRef` 43.
- Mantener el tratamiento especial ACEPTA para el tipo de referencia cuando corresponda.

## Seguridad

- Dry-run por defecto; emitir sólo con `--emitir-real`.
- Máximo dos documentos por defecto y `--procesar-todos` explícito.
- No guardar credenciales, endpoint real, datos personales ni respuestas productivas.
- Ocultar login y hash en el SOAP de previsualización.
- No realizar llamadas reales durante pruebas.

## Calidad y entregables

- Python 3.10–3.13.
- Pruebas para DTE 33, 39, 61, regla mensual, fechas futuras, montos, SOAP y largos.
- README, manual, INI de ejemplo, scripts Windows, VERSION y CHANGELOG.
- Versionado semántico; cualquier cambio al contrato de entrada debe incrementar versión mayor.
- Antes de producción, advertir que DTE 33/39 requiere homologación controlada con ambos facturadores.

Criterios de aceptación: compila, todas las pruebas pasan, el dry-run ficticio genera sólo OK y ningún archivo contiene secretos.

---
