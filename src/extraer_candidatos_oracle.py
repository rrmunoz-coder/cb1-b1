#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consulta Oracle y genera el CSV exacto del ETL. Nunca emite documentos."""

from __future__ import annotations

import argparse
import configparser
import csv
import logging
import os
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

VERSION = "2.0.0"
COLUMNAS_ENTRADA: Sequence[str] = (
    "MARCA", "RUT_EMISOR", "TIPO_DOC", "TIPO_SUSCRIPTOR", "RUT_CLIENTE",
    "NOMBRE", "GIRO", "DIRECCION", "COMUNA", "CIUDAD", "BILL_NO",
    "EMISION", "MONTO_DOC", "EMAIL", "TIPO_DOC_REF", "FOLIO_REBAJADO",
    "EMISION_BOLETA", "MONTO_NCRD",
)


def texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def es_verdadero(valor: str, default: bool = False) -> bool:
    normalizado = texto(valor).lower()
    if not normalizado:
        return default
    if normalizado in {"1", "true", "yes", "si", "sí", "s"}:
        return True
    if normalizado in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Valor booleano inválido: {valor!r}")


def primer_dia_mes_siguiente(fecha: date) -> date:
    return date(fecha.year + 1, 1, 1) if fecha.month == 12 else date(fecha.year, fecha.month + 1, 1)


def resolver_fecha_config(valor: str, *, es_hasta: bool) -> datetime:
    raw = texto(valor).upper()
    hoy = date.today()
    if raw in {"", "AUTO", "AUTO_MES_ACTUAL"} and not es_hasta:
        resultado = hoy.replace(day=1)
    elif raw in {"", "AUTO", "AUTO_MES_SIGUIENTE"} and es_hasta:
        resultado = primer_dia_mes_siguiente(hoy)
    else:
        try:
            resultado = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                f"Fecha inválida {valor!r}; usa YYYY-MM-DD, AUTO_MES_ACTUAL o AUTO_MES_SIGUIENTE"
            ) from exc
    return datetime.combine(resultado, datetime.min.time())


def cargar_ini(path: Path) -> configparser.ConfigParser:
    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Ejecuta instalacion\\instalar_windows.cmd o copia la plantilla del proyecto."
        )
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(path, encoding="utf-8")
    requeridas = ("ORACLE", "EXTRACCION_ORACLE", "ENTRADA_DEFAULTS", "ACEPTA", "CONDOR")
    faltan = [seccion for seccion in requeridas if not cfg.has_section(seccion)]
    if faltan:
        raise ValueError("Faltan secciones en el INI: " + ", ".join(faltan))
    return cfg


def resolver_password(cfg: configparser.ConfigParser) -> str:
    nombre_env = cfg.get("ORACLE", "password_env", fallback="").strip()
    if nombre_env and os.getenv(nombre_env):
        return os.environ[nombre_env]
    password = cfg.get("ORACLE", "password", fallback="")
    if password and not password.upper().startswith("COMPLETAR"):
        return password
    raise ValueError("Configura [ORACLE] password o password_env en el INI local")


def construir_binds(cfg: configparser.ConfigParser) -> Dict[str, Any]:
    desde = resolver_fecha_config(
        cfg.get("EXTRACCION_ORACLE", "fecha_desde", fallback="AUTO_MES_ACTUAL"),
        es_hasta=False,
    )
    hasta = resolver_fecha_config(
        cfg.get("EXTRACCION_ORACLE", "fecha_hasta", fallback="AUTO_MES_SIGUIENTE"),
        es_hasta=True,
    )
    if hasta <= desde:
        raise ValueError("fecha_hasta debe ser posterior a fecha_desde")
    return {
        "p_fecha_desde": desde,
        "p_fecha_hasta": hasta,
        "p_dias_para_vencimiento": cfg.getint("EXTRACCION_ORACLE", "dias_para_vencimiento", fallback=8),
        "p_dias_espera_bill_masivo": cfg.getint("EXTRACCION_ORACLE", "dias_espera_bill_masivo", fallback=2),
        "p_rut_emisor_claro": cfg.get("ACEPTA", "rut_emisor", fallback="94675000-K"),
        "p_rut_emisor_vtr": cfg.get("CONDOR", "rut_emisor", fallback="76114143-0"),
        "p_nombre_default": cfg.get("ENTRADA_DEFAULTS", "nombre", fallback=""),
        "p_giro_default": cfg.get("ENTRADA_DEFAULTS", "giro", fallback=""),
        "p_direccion_default": cfg.get("ENTRADA_DEFAULTS", "direccion", fallback=""),
        "p_comuna_default": cfg.get("ENTRADA_DEFAULTS", "comuna", fallback=""),
        "p_ciudad_default": cfg.get("ENTRADA_DEFAULTS", "ciudad", fallback=""),
        "p_email_default": cfg.get("ENTRADA_DEFAULTS", "email", fallback=""),
        "p_usar_emision_candidato_como_ref": int(es_verdadero(
            cfg.get(
                "ENTRADA_DEFAULTS",
                "usar_emision_candidato_como_fecha_referencia",
                fallback="false",
            )
        )),
    }


def normalizar_salida(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, Decimal):
        return str(int(valor)) if valor == valor.to_integral_value() else format(valor, "f")
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return texto(valor)


def a_decimal(valor: Any) -> Decimal | None:
    raw = texto(valor).replace("$", "").replace(" ", "")
    if not raw:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        izquierda, derecha = raw.rsplit(",", 1)
        raw = izquierda + ("." + derecha if len(derecha) != 3 else derecha)
    elif "." in raw:
        izquierda, derecha = raw.rsplit(".", 1)
        if len(derecha) == 3 and izquierda.replace("-", "").isdigit():
            raw = izquierda + derecha
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def validar_fila(row: Mapping[str, str]) -> List[str]:
    errores: List[str] = []
    obligatorios = (
        "MARCA", "RUT_EMISOR", "TIPO_DOC", "TIPO_SUSCRIPTOR", "RUT_CLIENTE",
        "NOMBRE", "DIRECCION", "COMUNA", "CIUDAD", "BILL_NO", "EMISION", "MONTO_DOC",
    )
    for campo in obligatorios:
        if not texto(row.get(campo)):
            errores.append(f"{campo} vacío")
    try:
        tipo_doc = int(Decimal(texto(row.get("TIPO_DOC"))))
    except (InvalidOperation, ValueError):
        tipo_doc = None
    if tipo_doc not in (33, 39, 61):
        errores.append(f"TIPO_DOC inválido: {texto(row.get('TIPO_DOC')) or '(vacío)'}")
    if tipo_doc == 33 and not texto(row.get("GIRO")):
        errores.append("GIRO vacío para DTE 33")
    monto_doc = a_decimal(row.get("MONTO_DOC"))
    if monto_doc is None or monto_doc <= 0:
        errores.append("MONTO_DOC inválido o <= 0")
    if tipo_doc == 61:
        for campo in ("TIPO_DOC_REF", "FOLIO_REBAJADO", "EMISION_BOLETA", "MONTO_NCRD"):
            if not texto(row.get(campo)):
                errores.append(f"{campo} vacío para NC")
        try:
            tipo_ref = int(Decimal(texto(row.get("TIPO_DOC_REF"))))
        except (InvalidOperation, ValueError):
            tipo_ref = None
        if tipo_ref not in (33, 39, 61):
            errores.append(f"TIPO_DOC_REF inválido: {texto(row.get('TIPO_DOC_REF')) or '(vacío)'}")
        monto_nc = a_decimal(row.get("MONTO_NCRD"))
        if monto_nc is None or monto_nc <= 0:
            errores.append("MONTO_NCRD inválido o <= 0")
        elif monto_doc is not None and monto_nc > monto_doc:
            errores.append("MONTO_NCRD mayor que MONTO_DOC")
    return errores


def escribir_csv(path: Path, columnas: Sequence[str], rows: Iterable[Mapping[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with path.open("w", encoding="utf-8-sig", newline="") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=list(columnas), extrasaction="ignore", delimiter=",")
        writer.writeheader()
        for row in rows:
            writer.writerow({campo: row.get(campo, "") for campo in columnas})
            total += 1
    return total


def conectar_oracle(cfg: configparser.ConfigParser):
    try:
        import oracledb
    except ImportError as exc:
        raise RuntimeError("Falta oracledb. Ejecuta instalacion\\instalar_windows.cmd") from exc
    if es_verdadero(cfg.get("ORACLE", "thick_mode", fallback="false")):
        lib_dir = cfg.get("ORACLE", "client_lib_dir", fallback="").strip()
        oracledb.init_oracle_client(lib_dir=lib_dir) if lib_dir else oracledb.init_oracle_client()
    user = cfg.get("ORACLE", "user", fallback="").strip()
    dsn = cfg.get("ORACLE", "dsn", fallback="").strip()
    if not user or user.upper().startswith("COMPLETAR"):
        raise ValueError("Configura [ORACLE] user")
    if not dsn or dsn.upper().startswith("COMPLETAR"):
        raise ValueError("Configura [ORACLE] dsn")
    return oracledb.connect(user=user, password=resolver_password(cfg), dsn=dsn)


def extraer(config_path: Path, sql_path: Path, output_path: Path, rejected_path: Path) -> Tuple[int, int]:
    cfg = cargar_ini(config_path)
    binds = construir_binds(cfg)
    sql = sql_path.read_text(encoding="utf-8")
    max_filas = cfg.getint("EXTRACCION_ORACLE", "max_filas", fallback=0)
    arraysize = cfg.getint("EXTRACCION_ORACLE", "arraysize", fallback=1000)
    logging.info(
        "Extracción Oracle | desde=%s | hasta=%s | vencimiento=+%s días",
        binds["p_fecha_desde"].date(), binds["p_fecha_hasta"].date(), binds["p_dias_para_vencimiento"],
    )
    validas: List[Dict[str, str]] = []
    rechazadas: List[Dict[str, str]] = []
    with conectar_oracle(cfg) as connection:
        with connection.cursor() as cursor:
            cursor.arraysize = arraysize
            cursor.execute(sql, binds)
            columnas_oracle = [descripcion[0].upper() for descripcion in cursor.description]
            faltantes = [c for c in COLUMNAS_ENTRADA if c not in columnas_oracle]
            if faltantes:
                raise RuntimeError("La consulta no devuelve el contrato completo: " + ", ".join(faltantes))
            for valores in cursor:
                raw = dict(zip(columnas_oracle, valores))
                row = {columna: normalizar_salida(raw.get(columna)) for columna in COLUMNAS_ENTRADA}
                errores = validar_fila(row)
                if errores:
                    rechazada = dict(row)
                    rechazada["MOTIVO_RECHAZO"] = " | ".join(errores)
                    rechazadas.append(rechazada)
                else:
                    validas.append(row)
                if max_filas > 0 and len(validas) + len(rechazadas) >= max_filas:
                    break
    escribir_csv(output_path, COLUMNAS_ENTRADA, validas)
    escribir_csv(rejected_path, tuple(COLUMNAS_ENTRADA) + ("MOTIVO_RECHAZO",), rechazadas)
    logging.info("Entrada ETL: %s | válidas=%s", output_path, len(validas))
    logging.info("Rechazados: %s | filas=%s", rejected_path, len(rechazadas))
    return len(validas), len(rechazadas)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genera el CSV del ETL desde Oracle")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--config", default="config_dte_onlinegeneration.ini")
    parser.add_argument("--sql", default="sql/candidatos_entrada_etl.sql")
    parser.add_argument("--output", default="reporte_diario.csv")
    parser.add_argument("--rechazados", default="salida_extraccion/candidatos_rechazados.csv")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", handlers=[logging.StreamHandler(sys.stdout)], force=True)
    try:
        validas, rechazadas = extraer(Path(args.config), Path(args.sql), Path(args.output), Path(args.rechazados))
    except Exception as exc:
        logging.error("Extracción fallida: %s", exc)
        raise SystemExit(1) from exc
    if validas == 0:
        logging.warning("No hay filas válidas; revisa candidatos_rechazados.csv y [ENTRADA_DEFAULTS]")
    if rechazadas:
        logging.warning("Hay %s candidato(s) rechazado(s); no entran al ETL", rechazadas)


if __name__ == "__main__":
    main()
