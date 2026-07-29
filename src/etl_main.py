from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from etl_common import __version__, cargar_config, leer_csv, setup_logging, split_rut, validar_columnas
from etl_layout import construir_args3, construir_payload
from etl_ws import construir_soap, emitir_ws, motor_section, normalizar_respuesta_acepta


CAMPOS_DEFAULT_INI = {
    "NOMBRE": "nombre",
    "GIRO": "giro",
    "DIRECCION": "direccion",
    "COMUNA": "comuna",
    "CIUDAD": "ciudad",
    "EMAIL": "email",
}


def aplicar_defaults_ini(row: Dict[str, str], cfg: Any) -> Tuple[Dict[str, str], List[str]]:
    """Completa sólo campos vacíos del CSV con valores fijos del INI.

    El valor presente en el CSV siempre tiene prioridad. Esta función no aplica
    defaults a RUT, folios, tipos de documento, fechas ni montos.
    """
    resultado = dict(row)
    usados: List[str] = []

    for campo_csv, clave_ini in CAMPOS_DEFAULT_INI.items():
        valor_csv = str(resultado.get(campo_csv) or "").strip()
        if valor_csv:
            continue

        valor_ini = cfg.get("VALORES_POR_DEFECTO", clave_ini, fallback="").strip()
        if valor_ini:
            resultado[campo_csv] = valor_ini
            usados.append(campo_csv)

    return resultado, usados


def escribir_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    campos: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in campos:
                campos.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def procesar(args: argparse.Namespace) -> Dict[str, Path]:
    out_dir = Path(args.out)
    log_path = setup_logging(out_dir)
    cfg = cargar_config(Path(args.config))

    input_path = Path(args.input)
    rows = leer_csv(input_path)
    validar_columnas(rows)

    if args.max_docs <= 0:
        raise SystemExit("--max-docs debe ser mayor que cero")

    total_entrada = len(rows)
    if args.procesar_todos:
        limite = total_entrada
    else:
        if total_entrada > args.max_docs and not args.permitir_mas_de_max:
            raise SystemExit(
                f"Seguridad: el archivo trae {total_entrada} filas y --max-docs={args.max_docs}. "
                "Recorta la entrada, usa --permitir-mas-de-max para procesar sólo las primeras N, "
                "o usa --procesar-todos de forma explícita."
            )
        limite = min(total_entrada, args.max_docs)

    rows = rows[:limite]
    input_sha256 = hashlib.sha256(input_path.read_bytes()).hexdigest()
    meses_referencia_nc = cfg.getint("REGLAS", "meses_documento_referencia_nc", fallback=1)
    glosa_b1 = cfg.get("DOCUMENTOS", "glosa_b1", fallback="Servicios de Telecomunicaciones")
    glosa_nc = cfg.get("DOCUMENTOS", "glosa_nc", fallback="Ajuste de Cargo Emitido")
    tipo_foliacion_e72 = cfg.get("GENERAL", "tipo_foliacion_e72", fallback="2")

    logging.info(
        "ETL versión=%s | archivo=%s | filas_entrada=%s | filas_a_procesar=%s | "
        "emitir_real=%s | meses_ref_nc=%s",
        __version__, input_path, total_entrada, len(rows), args.emitir_real, meses_referencia_nc,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    control: List[Dict[str, Any]] = []

    for idx, row_original in enumerate(rows, start=2):
        row, campos_default_ini = aplicar_defaults_ini(row_original, cfg)
        if campos_default_ini:
            logging.info(
                "Línea %s: valores del INI aplicados sólo por campos vacíos: %s",
                idx,
                ", ".join(campos_default_ini),
            )

        payload, errores = construir_payload(
            row,
            meses_referencia_nc=meses_referencia_nc,
            glosa_b1=glosa_b1,
            glosa_nc=glosa_nc,
        )
        folio_interno = args.folio_interno_inicial + len(control)
        base = {
            "VERSION_ETL": __version__,
            "ARCHIVO_ENTRADA": input_path.name,
            "SHA256_ENTRADA": input_sha256,
            "NRO_LINEA": idx,
            "BILL_NO": payload.get("BILL_NO", ""),
            "MOTOR": payload.get("MOTOR", ""),
            "RUT_EMISOR": payload.get("RUT_EMISOR", ""),
            "TIPO_DTE": payload.get("TIPO_DTE", ""),
            "FOLIO_INTERNO": folio_interno,
            "FOLIO_DTE": "",
            "URL_PDF": "",
            "TIPO_DOC_REF": payload.get("TIPO_DOC_REF", ""),
            "FOLIO_REF": payload.get("FOLIO_REF", ""),
            "FECHA_DTE_YYYYMMDD": payload.get("FECHA_DTE", ""),
            "FECHA_ORIGEN_CSV_YYYYMMDD": payload.get("FECHA_ORIGEN_CSV", ""),
            "FECHA_DOC_REF_YYYYMMDD": payload.get("FECHA_DOC_REF", ""),
            "MESES_REFERENCIA_NC": payload.get("MESES_REFERENCIA_NC", ""),
            "MONTO_DOC": payload.get("MONTO_DOC", ""),
            "MONTO_NCRD": payload.get("MONTO_NC", ""),
            "MONTO_TOTAL_DTE": payload.get("MONTO_TOTAL_DTE", ""),
            "MONTO_NETO": payload.get("MONTO_NETO", ""),
            "MONTO_IVA": payload.get("MONTO_IVA", ""),
            "COD_REF": payload.get("COD_REF", ""),
            "CAMPOS_DEFAULT_INI": ",".join(campos_default_ini),
            "ESTADO_EMISION": "",
            "DESCRIPCION_FALLA": "",
            "CODIGO_RESPUESTA": "",
            "MENSAJE_RESPUESTA": "",
            "FECHA_HORA": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if errores:
            base["ESTADO_EMISION"] = "NOK"
            base["DESCRIPCION_FALLA"] = " | ".join(errores)
            base["MENSAJE_RESPUESTA"] = base["DESCRIPCION_FALLA"]
            control.append(base)
            continue

        args3 = construir_args3(payload, folio_interno, tipo_foliacion_e72=tipo_foliacion_e72)
        safe_bill = re.sub(r"[^A-Za-z0-9_-]+", "_", payload["BILL_NO"])
        stem = f"DTE{payload['TIPO_DTE']}_{payload['MOTOR']}_{safe_bill}_{folio_interno}"
        args3_path = out_dir / f"{stem}_args3.txt"
        soap_path = out_dir / f"{stem}_request.xml"
        args3_path.write_text(args3, encoding="latin-1", errors="ignore")

        sec = motor_section(payload["MOTOR"])
        soap_preview = construir_soap(
            cfg.get(sec, "args0", fallback=split_rut(payload["RUT_EMISOR"])[0]),
            "***OCULTO***" if cfg.get(sec, "args1", fallback="") and not cfg.get(sec, "args1").upper().startswith("COMPLETAR") else "COMPLETAR_LOGIN",
            "***OCULTO***" if cfg.get(sec, "args2", fallback="") and not cfg.get(sec, "args2").upper().startswith("COMPLETAR") else "COMPLETAR_PASSWORD_O_HASH",
            args3,
            cfg.get("GENERAL", "args4", fallback="1"),
            cfg.get("GENERAL", "args5", fallback="2"),
        )
        soap_path.write_text(soap_preview, encoding="utf-8")

        if not args.emitir_real:
            base["ESTADO_EMISION"] = "OK"
            base["MENSAJE_RESPUESTA"] = f"DRY_RUN_OK. No emitido. TXT={args3_path.name}; SOAP={soap_path.name}"
            control.append(base)
            continue

        try:
            respuesta = emitir_ws(payload, args3, cfg)
            if payload.get("MOTOR") == "ACEPTA":
                respuesta = normalizar_respuesta_acepta(respuesta)
            raw_path = out_dir / f"{stem}_response.xml"
            raw_path.write_text(respuesta.raw_response, encoding="utf-8", errors="ignore")

            base["FOLIO_DTE"] = respuesta.folio_dte
            base["URL_PDF"] = respuesta.url_pdf
            base["CODIGO_RESPUESTA"] = respuesta.codigo
            base["MENSAJE_RESPUESTA"] = respuesta.mensaje

            if respuesta.estado == "EMITIDO_OK":
                base["ESTADO_EMISION"] = "OK"
            else:
                base["ESTADO_EMISION"] = "NOK"
                base["DESCRIPCION_FALLA"] = respuesta.mensaje or f"Respuesta no OK del facturador. Codigo={respuesta.codigo}"
            control.append(base)
        except Exception as exc:
            base["ESTADO_EMISION"] = "NOK"
            base["DESCRIPCION_FALLA"] = str(exc)
            base["MENSAJE_RESPUESTA"] = str(exc)
            control.append(base)

    control_path = out_dir / f"dte_control_emision_{ts}.csv"
    escribir_csv(control_path, control)

    ok = sum(1 for row in control if row.get("ESTADO_EMISION") == "OK")
    nok = len(control) - ok
    logging.info("Resumen: procesados=%s | OK=%s | NOK=%s", len(control), ok, nok)
    logging.info("Control único: %s", control_path)
    logging.info("Log: %s", log_path)
    return {"control": control_path, "log": log_path, "config": Path(args.config)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ETL emisión DTE 33, 39 y 61 OnlineGenerationDte ACEPTA/Cóndor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--input", required=True, help="CSV de entrada")
    parser.add_argument("--out", default="salida_dte_onlinegeneration", help="Carpeta de salida")
    parser.add_argument("--config", default="config_dte_onlinegeneration.ini", help="INI endpoint, credenciales y reglas")
    parser.add_argument("--max-docs", type=int, default=2, help="Máximo de documentos a procesar (por defecto: 2)")
    parser.add_argument("--permitir-mas-de-max", action="store_true", help="Acepta archivo mayor, pero procesa sólo los primeros --max-docs")
    parser.add_argument("--procesar-todos", action="store_true", help="Procesa todas las filas explícitamente")
    parser.add_argument("--folio-interno-inicial", type=int, default=1, help="Folio interno enviado en E3")
    parser.add_argument("--emitir-real", action="store_true", help="ENVÍA al WS. Sin esto sólo genera args3/SOAP")
    return parser


def main() -> None:
    procesar(build_parser().parse_args())
