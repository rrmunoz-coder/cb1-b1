# Seguridad

Este repositorio es público. Nunca se deben subir:

- `config_nc_onlinegeneration.ini` con endpoint, login o hash.
- CSV reales con RUT, nombre, dirección, correo, folio o monto.
- XML de solicitud/respuesta, TXT `args3`, logs o archivos de control.

La `.gitignore` excluye esos archivos. Antes de cada publicación, revisar `git status` y buscar credenciales o datos personales. El endpoint puede usar HTTP dentro de una red corporativa; no ejecutar fuera de la red autorizada ni exponer el tráfico a Internet.
