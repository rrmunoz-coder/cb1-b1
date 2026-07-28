# ETL CB1 / B1 — Emisión DTE 33, 39 y 61

ETL versionado para consultar candidatos en Oracle, generar el archivo de entrada y, sólo con confirmación explícita, emitir documentos mediante OnlineGenerationDte:

- `33`: factura electrónica B1.
- `39`: boleta electrónica B1.
- `61`: nota de crédito CB1.

El motor se selecciona por `RUT_EMISOR`: ACEPTA o Cóndor/Paperless.

**Versión actual:** `2.0.0`

## Flujo completo

```text
SCBILL.HP_CONSOLIDADO_ANDES_VTR_B1
              │
              ▼
src/extraer_candidatos_oracle.py
              │
              ├─ reporte_diario.csv
              └─ salida_extraccion/candidatos_rechazados.csv
                           │
                           ▼
         dry-run / emisión OnlineGenerationDte
```

La extracción Oracle **nunca emite documentos**. Sólo genera el CSV y separa los registros que no cumplen el contrato.

## Archivos locales en la raíz

Después de instalar, la raíz debe contener:

```text
cb1-b1\
├─ reporte_diario.csv
├─ config_dte_onlinegeneration.ini
├─ salida_extraccion\
├─ src\
├─ sql\
├─ scripts\
├─ instalacion\
├─ examples\
└─ tests\
```

`reporte_diario.csv`, las salidas operacionales y `config_dte_onlinegeneration.ini` quedan sólo en tu equipo y están excluidos de GitHub.

## Extracción desde Oracle

Completa en el INI local:

```ini
[ORACLE]
user = COMPLETAR_USUARIO
password = COMPLETAR_PASSWORD
dsn = COMPLETAR_HOST:1521/SERVICIO
thick_mode = false
client_lib_dir =

[EXTRACCION_ORACLE]
fecha_desde = AUTO_MES_ACTUAL
fecha_hasta = AUTO_MES_SIGUIENTE
dias_para_vencimiento = 8
dias_espera_bill_masivo = 2

[ENTRADA_DEFAULTS]
nombre =
giro =
direccion =
comuna =
ciudad =
email =
usar_emision_candidato_como_fecha_referencia = false
```

Luego ejecuta:

```bat
scripts\extraer_oracle.cmd
```

Para extraer y ejecutar inmediatamente el dry-run:

```bat
scripts\extraer_y_probar.cmd
```

Los campos descriptivos que no existen en la tabla se pueden completar en `[ENTRADA_DEFAULTS]`. Los montos, folios, tipos tributarios y fechas críticas nunca se inventan: si faltan, el candidato queda en `candidatos_rechazados.csv`.

## Contrato de entrada

El contrato no es retrocompatible. `TIPO_DOC` representa siempre el DTE que se emitirá. Para una NC se deben informar además `TIPO_DOC_REF`, `FOLIO_REBAJADO`, `EMISION_BOLETA` y `MONTO_NCRD`.

```text
MARCA,RUT_EMISOR,TIPO_DOC,TIPO_SUSCRIPTOR,RUT_CLIENTE,NOMBRE,GIRO,
DIRECCION,COMUNA,CIUDAD,BILL_NO,EMISION,MONTO_DOC,EMAIL,
TIPO_DOC_REF,FOLIO_REBAJADO,EMISION_BOLETA,MONTO_NCRD
```

Para CB1, la consulta intenta recuperar el documento original cruzando:

```text
FOLIO_REBAJADO = ID_DOC_PPL
```

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
scripts\extraer_y_probar.cmd
```

La prueba es un dry-run: genera los archivos de control y no llama al servicio de emisión.

Para una emisión real limitada a dos documentos:

```bat
scripts\ejecutar_real.cmd reporte_diario.csv
```

La emisión real exige escribir `EMITIR`.

## Advertencia de homologación

La generación NC conserva el layout previamente validado. La generación B1 `33/39` usa registros `E/D/G/T` y debe homologarse mediante dry-run y pruebas controladas con cada facturador antes de una emisión masiva.

Consulta [`instalacion/INSTALACION_Y_USO.md`](instalacion/INSTALACION_Y_USO.md) para la configuración completa, el mapeo Oracle y el uso operacional.
