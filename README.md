# ETL CB1 / B1 — Emisión NC DTE 61

Proyecto versionado para generar y, bajo confirmación explícita, emitir Notas de Crédito DTE 61 mediante OnlineGenerationDte, con ruteo a ACEPTA o Cóndor/Paperless según el RUT emisor.

**Versión actual:** `1.1.0`

## Seguridad primero

El repositorio es público. La configuración real, los CSV operacionales y las salidas con datos personales están excluidos mediante `.gitignore`. Sólo se incluye una configuración de ejemplo y un CSV ficticio.

## Estructura

- `src/`: ETL principal.
- `config/`: plantilla INI sin credenciales.
- `examples/`: CSV ficticio para pruebas.
- `instalacion/`: dependencias, instalación y manual de uso.
- `scripts/`: ejecución de prueba, emisión real limitada y pruebas automáticas.
- `tests/`: pruebas unitarias.
- `PROMPT_REGENERACION.md`: prompt maestro para reconstruir o evolucionar el código.
- `CHANGELOG.md`: control de versiones y cambios.

## Inicio rápido en Windows

```bat
instalacion\instalar_windows.cmd
scripts\probar_codigo.cmd
scripts\ejecutar_prueba.cmd
```

Luego completa `config_nc_onlinegeneration.ini` sólo en tu equipo. Para emisión real limitada a dos documentos:

```bat
scripts\ejecutar_real.cmd reporte_diario.csv
```

La emisión real exige escribir `EMITIR`. Para procesar todo el archivo se debe ejecutar manualmente con `--procesar-todos`; revisa primero el manual.

Consulta [`instalacion/INSTALACION_Y_USO.md`](instalacion/INSTALACION_Y_USO.md) para el detalle completo.
