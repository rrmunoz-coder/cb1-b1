# Instalación y uso

## 1. Requisitos

- Windows 10/11 o Windows Server con acceso autorizado a la red corporativa.
- Python 3.10 a 3.13, idealmente 64 bits.
- Acceso al endpoint OnlineGenerationDte.
- Login y password/hash para ACEPTA y Cóndor/Paperless.
- CSV con las columnas requeridas.

La única librería externa necesaria es `requests`; las demás usadas por el ETL pertenecen a la biblioteca estándar de Python.

## 2. Instalación automática

Desde la raíz del proyecto:

```bat
instalacion\instalar_windows.cmd
```

El script crea `.venv`, actualiza `pip`, instala `requests` y genera `config_nc_onlinegeneration.ini` desde la plantilla cuando no existe.

Equivalente manual:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r instalacion\requirements.txt
```

## 3. Configuración

Edita `config_nc_onlinegeneration.ini` en la raíz y completa:

- `[GENERAL] endpoint`
- `[ACEPTA] args1` y `args2`
- `[CONDOR] args1` y `args2`

No subas este archivo a GitHub. La `.gitignore` lo excluye.

## 4. Columnas del CSV

```text
MARCA,RUT_EMISOR,TIPO_DOC_TRIB,TIPO_SUSCRIPTOR,RUT_CLIENTE,NOMBRE,
DIRECCION,COMUNA,CIUDAD,BILL_NO,EMISION,FOLIO_REBAJADO,TIPO_DOC,
EMISION_BOLETA,MONTO_NCRD,MONTO_DOC,EMAIL
```

Reglas principales:

- `TIPO_DOC_TRIB` debe ser `61`.
- `TIPO_DOC` es el documento referenciado: `33`, `39` o `61`.
- `94675000-K` se enruta a ACEPTA.
- `76114143-0` se enruta a Cóndor/Paperless.
- `MONTO_NCRD` debe ser positivo y no superar `MONTO_DOC`.
- `COD_REF=1` cuando ambos montos son iguales; de lo contrario `COD_REF=3`.
- La fecha de la NC es el día de ejecución.

## 5. Pruebas automáticas

```bat
scripts\probar_codigo.cmd
```

Valida parseo de números/fechas, respuesta SOAP y largo de registros E/D/F/G/T.

## 6. Dry-run: no emite

Con datos ficticios:

```bat
scripts\ejecutar_prueba.cmd
```

Con un archivo específico:

```bat
scripts\ejecutar_prueba.cmd C:\ruta\reporte_diario.csv
```

También puede ejecutarse directamente:

```bat
.venv\Scripts\python.exe src\etl_emision_nc_onlinegeneration_real.py ^
  --input reporte_diario.csv ^
  --out salida_nc_prueba ^
  --config config_nc_onlinegeneration.ini ^
  --max-docs 2 ^
  --permitir-mas-de-max
```

Sin `--emitir-real`, sólo genera TXT `args3`, SOAP ocultando credenciales, log y CSV de control.

## 7. Emisión real limitada

```bat
scripts\ejecutar_real.cmd reporte_diario.csv
```

El script exige escribir `EMITIR` y procesa como máximo dos documentos.

## 8. Emisión real de todo el archivo

Primero ejecuta dry-run y revisa el CSV de control. Luego, sólo cuando corresponda:

```bat
.venv\Scripts\python.exe src\etl_emision_nc_onlinegeneration_real.py ^
  --input reporte_diario.csv ^
  --out salida_nc ^
  --config config_nc_onlinegeneration.ini ^
  --emitir-real ^
  --procesar-todos
```

`--procesar-todos` es explícito para evitar que un archivo grande sea emitido accidentalmente. El parámetro heredado `--permitir-mas-de-max` **no procesa todo**: sólo permite que el archivo sea mayor y toma las primeras `--max-docs` filas.

## 9. Archivos de salida

- `*_args3.txt`: layout posicional enviado en `args3`.
- `*_request.xml`: previsualización SOAP con login y hash ocultos.
- `*_response.xml`: respuesta completa cuando existe emisión real.
- `nc_control_emision_*.csv`: resultado homologado OK/NOK, folio, URL, mensaje, versión y SHA-256 de entrada.
- `etl_nc_*.log`: bitácora de ejecución.

## 10. Versiones

La versión está en `VERSION`, `__version__` y `CHANGELOG.md`. Para una nueva versión:

1. Crear una rama, por ejemplo `version/1.2.0`.
2. Modificar código y pruebas.
3. Ejecutar `scripts\probar_codigo.cmd` y un dry-run.
4. Actualizar `VERSION`, `__version__` y `CHANGELOG.md`.
5. Integrar mediante pull request o commit controlado.

## 11. Qué cargar en Python

El entorno requiere:

```text
requests>=2.31.0,<3.0.0
```

Instalación directa:

```bat
python -m pip install "requests>=2.31.0,<3.0.0"
```
