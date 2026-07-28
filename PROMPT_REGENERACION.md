# Prompt maestro para regenerar o evolucionar el ETL

Usa este prompt junto con la última versión del código, el changelog, el manual y ejemplos sin datos reales.

---

Actúa como desarrollador senior Python especializado en ETL financiero, Oracle, DTE chilenos, SOAP y controles auditables. Regenera o mejora el proyecto **ETL CB1/B1 — extracción Oracle y emisión DTE 33, 39 y 61 por OnlineGenerationDte**.

## Arquitectura obligatoria

1. Separar estrictamente la extracción Oracle de la emisión.
2. La extracción sólo debe consultar Oracle y generar archivos CSV; nunca debe emitir.
3. La fuente de candidatos es `SCBILL.HP_CONSOLIDADO_ANDES_VTR_B1`.
4. La entrada válida debe contener exactamente: `MARCA,RUT_EMISOR,TIPO_DOC,TIPO_SUSCRIPTOR,RUT_CLIENTE,NOMBRE,GIRO,DIRECCION,COMUNA,CIUDAD,BILL_NO,EMISION,MONTO_DOC,EMAIL,TIPO_DOC_REF,FOLIO_REBAJADO,EMISION_BOLETA,MONTO_NCRD`.
5. Los registros incompletos deben ir a un CSV separado con `MOTIVO_RECHAZO`.
6. Credenciales Oracle y del facturador sólo en el INI local o variables de entorno; nunca en GitHub.

## Detección Oracle

Mantener estos filtros configurables:

- Folio que contenga `B1-` o `CB1-`.
- `CURRENT_TOTAL > 0`.
- `DUE > 0`.
- Marca `CLARO` o `VTR`.
- `TIPO_DOC` original `33` o `39`.
- Suscriptor `Fijo` o `Movil`.
- `CURRENT_TOTAL + WRITEOFF > 0`.
- Rango de `EMISION`.
- Vencimiento a N días desde `SYSDATE`.
- Bill Masivo con espera configurable; otros tipos con emisión anterior a `SYSDATE`.

Para CB1:

- `TIPO_DOC` de salida = `61`.
- Intentar recuperar el documento original cruzando `FOLIO_REBAJADO = ID_DOC_PPL`, misma marca y mismo RUT.
- `TIPO_DOC_REF` = tipo del documento original.
- `EMISION_BOLETA` = emisión del documento original.
- `MONTO_DOC` = `MONTO_FOLIO_REBAJADO`, con respaldo en el documento encontrado.
- `MONTO_NCRD` = valor absoluto de `MONTO_NC`.
- No inventar montos, folios, tipos, RUT ni fechas tributarias.
- `usar_emision_candidato_como_fecha_referencia` debe ser `false` por defecto y sólo habilitarse manualmente después de validación funcional.

## Valores de respaldo

- `NOMBRE`: Oracle `NOMBRE_CLARO`, luego `NAME`, luego INI.
- `GIRO`, `DIRECCION`, `COMUNA`, `CIUDAD` y `EMAIL`: variables configurables en `[ENTRADA_DEFAULTS]`.
- Si falta un dato obligatorio, rechazar el candidato.
- Para DTE 33, `GIRO` es obligatorio.
- `EMAIL` puede ser vacío.

## Contrato funcional de emisión

1. `TIPO_DOC` representa siempre el DTE a emitir: `33`, `39` o `61`.
2. No implementar compatibilidad con esquemas antiguos ni usar `TIPO_DOC_TRIB` como sustituto del contrato.
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
- La extracción Oracle no debe encadenar una emisión real.
- El flujo `extraer_y_probar` sólo debe ejecutar dry-run.

## Calidad y entregables

- Python 3.10–3.13.
- `requests` para SOAP y `python-oracledb` para Oracle.
- Soportar modo Thin y Thick configurables.
- SQL parametrizado mediante binds; no concatenar credenciales ni fechas.
- Pruebas para extracción, contrato de 18 columnas, rechazos, DTE 33, 39, 61, regla mensual, fechas futuras, montos, SOAP y largos.
- README, manual, INI de ejemplo, scripts Windows, VERSION y CHANGELOG.
- Versionado semántico; cualquier cambio al contrato de entrada debe incrementar versión mayor.
- Antes de producción, advertir que DTE 33/39 y el cruce CB1 requieren homologación controlada.

Criterios de aceptación: compila, todas las pruebas pasan, el dry-run ficticio genera sólo OK, la extracción genera el contrato exacto y ningún archivo contiene secretos.

---
