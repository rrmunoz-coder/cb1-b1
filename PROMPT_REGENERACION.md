# Prompt maestro para regenerar o evolucionar el ETL

Usa el siguiente prompt junto con la última versión del código, el `CHANGELOG.md`, el manual y ejemplos **sin datos reales**:

---

Actúa como desarrollador senior Python especializado en ETL financiero, facturación electrónica chilena, SOAP y controles auditables. Regenera o mejora el proyecto **ETL CB1/B1 — emisión de Notas de Crédito DTE 61 por OnlineGenerationDte**, manteniendo compatibilidad funcional y control de versiones.

## Objetivo funcional

Procesar un CSV y construir una NC DTE 61. Enrutar por `RUT_EMISOR`:

- `94675000-K` → motor `ACEPTA`.
- `76114143-0` → motor `CONDOR`/Paperless.

Aplicar estas reglas:

1. `TIPO_DOC_TRIB=61`.
2. `TIPO_DOC` es el documento referenciado y admite 33, 39 o 61.
3. `COD_REF=1` cuando `MONTO_NCRD == MONTO_DOC`; en otro caso `COD_REF=3`.
4. Rechazar `MONTO_NCRD > MONTO_DOC` y montos no positivos.
5. Glosa fija: `Ajuste de Cargo Emitido`.
6. Documento afecto: `neto=round(total/1.19)` e `IVA=total-neto`.
7. `FECHA_NC` corresponde al día de ejecución; `EMISION_BOLETA` es la fecha del documento referenciado.
8. El folio real lo asigna el facturador y se obtiene desde `Mensaje` con formato `folio|url`.

## Restricciones técnicas críticas

- Conservar exactamente los layouts posicionales E, D, F, G y T y sus largos: 1405, 2075, 185, 123 y 70.
- En la referencia F, mantener `FchRef` en posiciones 35–42 y `CodRef` en 43.
- Para ACEPTA, conservar el tratamiento especial del tipo referenciado sin cero izquierdo cuando corresponda.
- Soportar CSV UTF-8, UTF-8-SIG, Latin-1 y CP1252; detectar delimitador `; , | tab`.
- Soportar fechas ISO, DD/MM/YYYY, YYYYMMDD, DDMMYYYY y serial Excel.
- Soportar enteros Excel como `39.0` y montos chilenos como `23.000` sin alterar su valor.
- Mantener dry-run por defecto. Sólo emitir con `--emitir-real`.
- Mantener límite seguro de dos documentos y un parámetro explícito `--procesar-todos`.
- Nunca guardar credenciales reales en código, pruebas, logs, XML de previsualización ni repositorio.
- Ocultar tanto login como password/hash en el SOAP de previsualización.
- No incluir CSV reales, RUT de clientes, nombres, direcciones, correos ni respuestas operacionales.
- Conservar salida de control con estado OK/NOK, folio, URL, código, mensaje, versión del ETL y SHA-256 del archivo de entrada.
- No realizar llamadas reales al web service durante pruebas automáticas.

## Entregables

1. Código Python compatible con Python 3.10–3.13.
2. `requirements.txt` mínimo y con versiones acotadas.
3. Configuración `.ini.example` sin secretos ni endpoint interno real.
4. Scripts Windows para instalar, probar, hacer dry-run y emitir un máximo de dos documentos con confirmación.
5. Pruebas unitarias para números, fechas, respuesta SOAP, validaciones y largos E/D/F/G/T.
6. README, manual de instalación/uso, `.gitignore`, `SECURITY.md`, `VERSION` y `CHANGELOG.md`.
7. Indicar claramente la nueva versión semántica y justificar cada cambio.

## Criterios de aceptación

- `python -m py_compile` termina sin errores.
- `python -m unittest discover -s tests -v` pasa completamente.
- Un dry-run con datos ficticios genera control OK y no llama al endpoint.
- Ningún archivo entregado contiene secretos, endpoint interno real o datos personales.
- Toda modificación que afecte layouts, reglas tributarias o emisión real debe quedar destacada como cambio de alto riesgo.

Antes de devolver el resultado, compara la nueva versión con la anterior, enumera riesgos residuales y actualiza el historial de cambios.

---
