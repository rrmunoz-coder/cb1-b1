#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Punto de entrada compatible del ETL CB1/B1, versión 1.1.0."""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from etl_common import __version__, parse_fecha_yyyymmdd, parse_int, parse_monto
from etl_layout import construir_args3, construir_payload
from etl_main import build_parser, main, procesar
from etl_ws import parsear_respuesta_ws

__all__ = [
    "__version__", "parse_fecha_yyyymmdd", "parse_int", "parse_monto",
    "construir_args3", "construir_payload", "parsear_respuesta_ws",
    "build_parser", "procesar", "main",
]

if __name__ == "__main__":
    main()
