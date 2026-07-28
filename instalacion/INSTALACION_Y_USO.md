# Instalación y uso — ETL CB1/B1 v2.0.0

## 1. Requisitos

- Windows 10/11 o Windows Server.
- Python 3.10 a 3.13 de 64 bits.
- Acceso autorizado al endpoint OnlineGenerationDte.
- Credenciales para ACEPTA y Cóndor/Paperless.
- Biblioteca Python `requests`.

## 2. Instalación

Desde la raíz:

```bat
instalacion\instalar_windows.cmd
```

El instalador crea `.venv`, instala dependencias y copia la plantilla como `config_nc_onlinegeneration.ini` cuando el archivo no existe.

Instalación manual:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r instalacion\requirements.txt
```

## 3. Configuración

Completa localmente:

```ini
[GENERAL]
endpoint = COMPLETAR_ENDPOINT_INTERNO

[REGLAS]
meses_documento_referencia_nc = 1

[DOCUMENTOS]
glosa_b1 = Servicios de Telecomunicaciones
glosa_nc = Ajuste de Cargo Emitido
```

Interpretación de `meses_documento_referencia_nc`:

- `0`: sólo documentos del mes de ejecución.
- `1`: mes de ejecución o mes anterior.
- `2`: mes de ejecución o hasta dos meses anteriores.

La regla usa meses calendario. Una NC ejecutada el 28 de julio con valor `1` acepta cualquier fecha de junio o julio, pero rechaza mayo y agosto.

## 4. Contrato del CSV v2

Cabecera recomendada:

```text
MARCA,RUT_EMISOR,TIPO_DOC,TIPO_SUSCRIPTOR,RUT_CLIENTE,NOMBRE,GIRO,
DIRECCION,COMUNA,CIUDAD,BILL_NO,EMISION,MONTO_DOC,EMAIL,
TIPO_DOC_REF,FOLIO_REBAJADO,EMISION_BOLETA,MONTO_NCRD
```

### Campos comunes

- `TIPO_DOC`: DTE que se emitirá: `33`, `39` o `61`.
- `EMISION`: fecha del B1. Para NC queda informativa porque la fecha de la NC es la fecha de ejecución.
- `MONTO_DOC`: total del B1 o total del documento original cuando se emite una NC.
- `GIRO`: obligatorio para factura `33`; opcional para `39` y `61`.

### Campos exclusivos para NC 61

- `TIPO_DOC_REF`: tipo del documento referenciado: `33`, `39` o `61`.
- `FOLIO_REBAJADO`: folio referenciado.
- `EMISION_BOLETA`: fecha de emisión del documento referenciado.
- `MONTO_NCRD`: monto total de la NC.

Reglas NC:

- `MONTO_NCRD` debe ser positivo.
- `MONTO_NCRD` no puede superar `MONTO_DOC`.
- `COD_REF=1` cuando ambos montos son iguales; en otro caso `COD_REF=3`.
- La fecha referenciada debe cumplir el rango mensual del INI.

## 5. Layout generado

- B1 `33/39`: `E`, `D`, `G`, `T` con largos `1405`, `2075`, `123`, `70`.
- NC `61`: `E`, `D`, `F`, `G`, `T` con largos `1405`, `2075`, `185`, `123`, `70`.
- En NC, `FchRef` permanece en posiciones 35–42 y `CodRef` en 43.

## 6. Pruebas

```bat
scripts\probar_codigo.cmd
scripts\ejecutar_prueba.cmd
```

El segundo comando procesa el CSV ficticio completo en dry-run. No llama al endpoint.

## 7. Emisión real limitada

```bat
scripts\ejecutar_real.cmd reporte_diario.csv
```

Exige escribir `EMITIR` y procesa máximo dos documentos.

## 8. Emisión real completa

Después de revisar el dry-run:

```bat
.venv\Scripts\python.exe src\etl_emision_dte_onlinegeneration_real.py ^
  --input reporte_diario.csv ^
  --out salida_dte ^
  --config config_nc_onlinegeneration.ini ^
  --emitir-real ^
  --procesar-todos
```

## 9. Salidas

- `*_args3.txt`: layout posicional.
- `*_request.xml`: SOAP de previsualización sin credenciales visibles.
- `*_response.xml`: respuesta real del facturador.
- `dte_control_emision_*.csv`: control OK/NOK, tipo DTE, folio, montos y regla NC.
- `etl_dte_*.log`: bitácora.

## 10. Dependencia Python

```text
requests>=2.31.0,<3.0.0
```

## 11. Homologación necesaria

Antes de emitir B1 en volumen, ejecutar casos controlados de DTE 33 y 39 en ambos motores y validar PDF, folio, montos, giro receptor, fecha y contabilización. Las NC mantienen la estructura de referencia ya utilizada, agregando únicamente la restricción mensual configurable.
