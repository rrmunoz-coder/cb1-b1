# Instalación y uso — ETL CB1/B1 v2.0.0

## 1. Objetivo

El proyecto realiza dos etapas separadas:

1. Consulta Oracle y genera `reporte_diario.csv` con el contrato exacto del ETL.
2. Valida, genera el layout y, sólo con confirmación explícita, emite DTE `33`, `39` o `61` por OnlineGenerationDte.

La extracción Oracle nunca llama al servicio de emisión.

## 2. Requisitos

- Windows 10/11 o Windows Server.
- Python 3.10 a 3.13 de 64 bits.
- Acceso Oracle a `SCBILL.HP_CONSOLIDADO_ANDES_VTR_B1`.
- Acceso autorizado a OnlineGenerationDte.
- Credenciales para ACEPTA y Cóndor/Paperless.
- Bibliotecas Python `requests` y `oracledb`.
- Instant Client sólo cuando se configure `thick_mode = true`.

## 3. Instalación

```bat
instalacion\instalar_windows.cmd
```

El instalador crea `.venv`, instala dependencias y copia la plantilla como `config_dte_onlinegeneration.ini` cuando el archivo no existe.

Instalación manual:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r instalacion\requirements.txt
```

## 4. Configuración Oracle

```ini
[ORACLE]
user = COMPLETAR_USUARIO
password = COMPLETAR_PASSWORD
password_env =
dsn = COMPLETAR_HOST:1521/SERVICIO
thick_mode = false
client_lib_dir =
```

La contraseña puede cargarse desde una variable de entorno:

```ini
password =
password_env = ORACLE_PASSWORD_CB1
```

```bat
set ORACLE_PASSWORD_CB1=CLAVE_LOCAL
```

Modo Thin:

```ini
thick_mode = false
```

Modo Thick:

```ini
thick_mode = true
client_lib_dir = C:\Oracle\product\instantclient_19_19
```

## 5. Filtros de candidatos

```ini
[EXTRACCION_ORACLE]
fecha_desde = AUTO_MES_ACTUAL
fecha_hasta = AUTO_MES_SIGUIENTE
dias_para_vencimiento = 8
dias_espera_bill_masivo = 2
arraysize = 1000
max_filas = 0
```

También se pueden indicar fechas manuales:

```ini
fecha_desde = 2026-07-01
fecha_hasta = 2026-08-01
```

`fecha_hasta` es exclusiva. El ejemplo consulta julio de 2026.

La consulta conserva estos criterios:

- Folio que contiene `B1-` o `CB1-`.
- `CURRENT_TOTAL > 0`.
- `DUE > 0`.
- Marca `CLARO` o `VTR`.
- Tipo original `33` o `39`.
- Suscriptor `Fijo` o `Movil`.
- `CURRENT_TOTAL + WRITEOFF > 0`.
- Rango de `EMISION`.
- Vencimiento a la cantidad de días configurada.
- Bill Masivo con la espera indicada.
- Otros tipos con emisión anterior a `SYSDATE`.

## 6. Valores manuales para datos no disponibles

```ini
[ENTRADA_DEFAULTS]
nombre =
giro =
direccion =
comuna =
ciudad =
email =
usar_emision_candidato_como_fecha_referencia = false
```

Reglas:

- `NOMBRE` se obtiene primero desde `NOMBRE_CLARO`.
- Si está vacío, se usa `NAME`.
- Si ambos están vacíos, se usa `nombre` del INI.
- `GIRO`, `DIRECCION`, `COMUNA`, `CIUDAD` y `EMAIL` se completan desde el INI porque no están en la tabla entregada.
- `GIRO` es obligatorio para DTE `33`.
- `EMAIL` puede quedar vacío.
- Si falta un campo obligatorio, el registro se rechaza y no llega a `reporte_diario.csv`.

Los valores manuales no se utilizan para montos, folios, tipos de documento, RUT ni fechas tributarias. Esos datos deben venir de Oracle.

## 7. Recuperación del documento referenciado CB1

La consulta clasifica:

```text
B1-  → TIPO_DOC 33 o 39
CB1- → TIPO_DOC 61
```

Para CB1 intenta recuperar el documento original mediante:

```text
FOLIO_REBAJADO = ID_DOC_PPL
```

El cruce también exige la misma `MARCA` y el mismo `RUT`.

| Campo de entrada | Fuente |
|---|---|
| `TIPO_DOC` | `61` |
| `TIPO_DOC_REF` | tipo del documento encontrado; respaldo `TIPO_DOC` candidato |
| `FOLIO_REBAJADO` | `FOLIO_REBAJADO` |
| `EMISION_BOLETA` | `EMISION` del documento encontrado |
| `MONTO_DOC` | `MONTO_FOLIO_REBAJADO`; respaldo `CURRENT_TOTAL` del documento encontrado |
| `MONTO_NCRD` | valor absoluto de `MONTO_NC` |

Por seguridad:

```ini
usar_emision_candidato_como_fecha_referencia = false
```

Con `false`, si no se encuentra la fecha original, el CB1 queda rechazado. Sólo después de validar funcionalmente que `EMISION` del candidato corresponde al documento rebajado se puede cambiar a `true`.

## 8. Generación del archivo de entrada

```bat
scripts\extraer_oracle.cmd
```

Salidas:

```text
reporte_diario.csv
salida_extraccion\candidatos_rechazados.csv
```

`reporte_diario.csv` contiene exclusivamente estas 18 columnas:

```text
MARCA,RUT_EMISOR,TIPO_DOC,TIPO_SUSCRIPTOR,RUT_CLIENTE,NOMBRE,GIRO,
DIRECCION,COMUNA,CIUDAD,BILL_NO,EMISION,MONTO_DOC,EMAIL,
TIPO_DOC_REF,FOLIO_REBAJADO,EMISION_BOLETA,MONTO_NCRD
```

El archivo de rechazados agrega `MOTIVO_RECHAZO`.

## 9. Mapeo B1

| Campo de entrada | Fuente |
|---|---|
| `MARCA` | `MARCA` |
| `RUT_EMISOR` | ACEPTA para CLARO; CONDOR para VTR |
| `TIPO_DOC` | `TIPO_DOC` original, `33` o `39` |
| `TIPO_SUSCRIPTOR` | `TIPO_SUSCRIPTOR` |
| `RUT_CLIENTE` | `RUT` |
| `NOMBRE` | `NOMBRE_CLARO`, luego `NAME`, luego INI |
| `BILL_NO` | `FOLIO` |
| `EMISION` | `EMISION` |
| `MONTO_DOC` | `CURRENT_TOTAL` |
| Campos NC | vacíos |

## 10. Reglas del contrato

### Campos comunes

- `TIPO_DOC`: DTE a emitir: `33`, `39` o `61`.
- `EMISION`: fecha del B1. Para NC queda informativa porque la fecha de la NC es el día de ejecución.
- `MONTO_DOC`: total del B1 o total del documento original para NC.
- `GIRO`: obligatorio para factura `33`; opcional para `39` y `61`.

### Campos exclusivos para NC 61

- `TIPO_DOC_REF`: tipo del documento referenciado.
- `FOLIO_REBAJADO`: folio tributario referenciado.
- `EMISION_BOLETA`: fecha del documento referenciado.
- `MONTO_NCRD`: monto total de la NC.

Reglas NC:

- `MONTO_NCRD` debe ser positivo.
- `MONTO_NCRD` no puede superar `MONTO_DOC`.
- `COD_REF=1` cuando ambos montos son iguales.
- `COD_REF=3` cuando son distintos.
- La fecha referenciada debe cumplir el rango mensual del INI.

## 11. Regla mensual de referencias

```ini
[REGLAS]
meses_documento_referencia_nc = 1
```

- `0`: sólo documentos del mes de ejecución.
- `1`: mes de ejecución o mes anterior.
- `2`: mes de ejecución o hasta dos meses anteriores.

## 12. Pruebas

```bat
scripts\probar_codigo.cmd
scripts\extraer_y_probar.cmd
```

El segundo comando consulta Oracle y ejecuta sólo un dry-run.

También puede probar un CSV existente:

```bat
scripts\ejecutar_prueba.cmd reporte_diario.csv
```

## 13. Emisión real limitada

```bat
scripts\ejecutar_real.cmd reporte_diario.csv
```

Exige escribir `EMITIR` y procesa máximo dos documentos.

## 14. Emisión real completa

```bat
.venv\Scripts\python.exe src\etl_emision_dte_onlinegeneration_real.py ^
  --input reporte_diario.csv ^
  --out salida_dte ^
  --config config_dte_onlinegeneration.ini ^
  --emitir-real ^
  --procesar-todos
```

## 15. Layout generado

- B1 `33/39`: `E`, `D`, `G`, `T` con largos `1405`, `2075`, `123`, `70`.
- NC `61`: `E`, `D`, `F`, `G`, `T` con largos `1405`, `2075`, `185`, `123`, `70`.
- En NC, `FchRef` permanece en posiciones 35–42 y `CodRef` en 43.

## 16. Dependencias

```text
requests>=2.31.0,<3.0.0
oracledb>=3.4.0,<4.0.0
```

Se mantiene `python-oracledb` 3.x para Python 3.13 y compatibilidad con ambientes Oracle anteriores mediante modo Thick cuando corresponda.

## 17. Homologación necesaria

Antes de emitir en volumen, validar casos controlados de DTE 33 y 39 en ambos motores.

Para CB1, validar además:

- que `FOLIO_REBAJADO` corresponda a `ID_DOC_PPL`;
- que `EMISION_BOLETA` sea la fecha del documento original;
- que `MONTO_FOLIO_REBAJADO` sea el total original;
- que `MONTO_NC` tenga el signo y valor esperados.
