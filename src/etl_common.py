from __future__ import annotations

import configparser
import csv
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RUT_ACEPTA = "94675000-K"
RUT_CONDOR = "76114143-0"
TIPOS_DTE_SOPORTADOS = (33, 39, 61)
TIPO_DTE_NC = 61
GLOSA_B1_DEFAULT = "Servicios de Telecomunicaciones"
GLOSA_NC_DEFAULT = "Ajuste de Cargo Emitido"
IVA = 0.19
__version__ = "2.0.0"
DEFAULT_ENDPOINT = ""
SOAP_NS = "http://www.w3.org/2003/05/soap-envelope"
WEB_NS = "http://webservices.online.webapp.paperless.cl"

COLUMNAS_BASE_OBLIGATORIAS = [
    "MARCA", "RUT_EMISOR", "TIPO_DOC", "TIPO_SUSCRIPTOR", "RUT_CLIENTE",
    "NOMBRE", "DIRECCION", "COMUNA", "CIUDAD", "BILL_NO", "EMISION",
    "MONTO_DOC", "EMAIL",
]
COLUMNAS_NC_OBLIGATORIAS = [
    "TIPO_DOC_REF", "FOLIO_REBAJADO", "EMISION_BOLETA", "MONTO_NCRD",
]
COLUMNAS_FACTURA_OBLIGATORIAS = ["GIRO"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class RespuestaWS:
    estado: str
    folio_dte: str = ""
    url_pdf: str = ""
    codigo: str = ""
    mensaje: str = ""
    raw_response: str = ""


def setup_logging(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"etl_dte_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    return log_path


def crear_config_ejemplo(path: Path) -> None:
    if path.exists():
        return
    path.write_text(f"""# Configuración para WS OnlineGenerationDte
# No guardar credenciales reales en GitHub.

[GENERAL]
endpoint = COMPLETAR_ENDPOINT_INTERNO
timeout_segundos = 60
reintentos = 1
pausa_reintento_segundos = 3
args4 = 1
args5 = 2
tipo_foliacion_e72 = 2

[REGLAS]
# 0 = sólo mes actual; 1 = mes actual o mes anterior; 2 = hasta dos meses anteriores.
meses_documento_referencia_nc = 1

[DOCUMENTOS]
glosa_b1 = {GLOSA_B1_DEFAULT}
glosa_nc = {GLOSA_NC_DEFAULT}

[ACEPTA]
rut_emisor = 94675000-K
args0 = 94675000
args1 = COMPLETAR_LOGIN
args2 = COMPLETAR_PASSWORD_O_HASH

[CONDOR]
rut_emisor = 76114143-0
args0 = 76114143
args1 = COMPLETAR_LOGIN
args2 = COMPLETAR_PASSWORD_O_HASH
""", encoding="utf-8")


def cargar_config(path: Path) -> configparser.ConfigParser:
    crear_config_ejemplo(path)
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    meses = cfg.getint("REGLAS", "meses_documento_referencia_nc", fallback=1)
    if meses < 0:
        raise ValueError("[REGLAS] meses_documento_referencia_nc no puede ser negativo")
    return cfg


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def texto(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def texto_latin1(v: Any) -> str:
    s = strip_accents(texto(v))
    return s.encode("latin-1", errors="ignore").decode("latin-1")


def normalizar_nombre_columna(s: str) -> str:
    s = strip_accents(str(s)).strip().upper()
    s = re.sub(r"[^A-Z0-9_]+", "_", s)
    return s.strip("_")


def normalizar_rut(v: Any) -> str:
    return texto(v).upper().replace(".", "")


def split_rut(rut: str) -> Tuple[str, str]:
    rut = normalizar_rut(rut)
    if "-" in rut:
        cuerpo, dv = rut.split("-", 1)
        return re.sub(r"\D", "", cuerpo), dv[:1].upper()
    solo = re.sub(r"[^0-9Kk]", "", rut)
    return re.sub(r"\D", "", solo[:-1]), solo[-1:].upper()


def _normalizar_numero(v: Any, *, monto: bool) -> Optional[str]:
    """Normaliza enteros de Excel y separadores de miles/decimales chilenos."""
    s = texto(v).replace("$", "").replace(" ", "")
    s = re.sub(r"[^0-9,._+\-]", "", s).replace("_", "")
    if not s:
        return None

    if re.fullmatch(r"[+\-]?\d{1,3}(?:[.,]\d{3})+", s):
        return s.replace(".", "").replace(",", "")

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            return s.replace(".", "").replace(",", ".")
        return s.replace(",", "")

    if "," in s:
        izquierda, derecha = s.rsplit(",", 1)
        if monto and len(derecha) == 3 and izquierda.replace("+", "").replace("-", "").isdigit():
            return izquierda + derecha
        return izquierda + "." + derecha

    if "." in s:
        izquierda, derecha = s.rsplit(".", 1)
        if monto and len(derecha) == 3 and izquierda.replace("+", "").replace("-", "").isdigit():
            return izquierda + derecha
        return s

    return s


def parse_int(v: Any) -> Optional[int]:
    s = _normalizar_numero(v, monto=False)
    if s is None:
        return None
    try:
        n = float(s)
        if not n.is_integer():
            return None
        return int(n)
    except (TypeError, ValueError, OverflowError):
        return None


def parse_monto(v: Any) -> Optional[int]:
    s = _normalizar_numero(v, monto=True)
    if s is None:
        return None
    try:
        return int(round(float(s)))
    except (TypeError, ValueError, OverflowError):
        return None


def parse_fecha_yyyymmdd(v: Any) -> Optional[str]:
    """Normaliza fechas ISO, DD/MM/YYYY, compactas y seriales Excel."""
    s = texto(v)
    if not s:
        return None
    s = s.strip().strip('"').strip("'")

    if re.fullmatch(r"\d{5}(?:\.0+)?", s):
        try:
            from datetime import timedelta
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=int(float(s)))).strftime("%Y%m%d")
        except Exception:
            pass

    s10 = s[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y.%m.%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s10, fmt).strftime("%Y%m%d")
        except Exception:
            pass

    digits = re.sub(r"\D", "", s)
    if len(digits) >= 8:
        d8 = digits[:8]
        if 1900 <= int(d8[:4]) <= 2100:
            try:
                datetime.strptime(d8, "%Y%m%d")
                return d8
            except Exception:
                pass
        candidato = d8[4:8] + d8[2:4] + d8[0:2]
        try:
            datetime.strptime(candidato, "%Y%m%d")
            return candidato
        except Exception:
            pass
    return None


def diferencia_meses(fecha_anterior_yyyymmdd: str, fecha_actual_yyyymmdd: str) -> int:
    anterior = datetime.strptime(fecha_anterior_yyyymmdd, "%Y%m%d")
    actual = datetime.strptime(fecha_actual_yyyymmdd, "%Y%m%d")
    return (actual.year - anterior.year) * 12 + actual.month - anterior.month


def validar_mes_referencia_nc(
    fecha_referencia_yyyymmdd: str,
    fecha_emision_nc_yyyymmdd: str,
    meses_permitidos: int,
) -> Tuple[bool, int]:
    """Valida por mes calendario; 1 permite el mes actual y el inmediatamente anterior."""
    diferencia = diferencia_meses(fecha_referencia_yyyymmdd, fecha_emision_nc_yyyymmdd)
    return 0 <= diferencia <= meses_permitidos, diferencia


def leer_csv(path: Path) -> List[Dict[str, str]]:
    last_error = None
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            sample = path.read_text(encoding=enc, errors="strict")[:4096]
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f, dialect=dialect)
                if not reader.fieldnames:
                    raise ValueError("CSV sin cabecera")
                field_map = {name: normalizar_nombre_columna(name) for name in reader.fieldnames}
                rows: List[Dict[str, str]] = []
                for row in reader:
                    rows.append({field_map[k]: (v or "") for k, v in row.items() if k is not None})
            logging.info("CSV leído OK: %s | encoding=%s | filas=%s", path, enc, len(rows))
            return rows
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"No pude leer CSV {path}: {last_error}")


def validar_columnas(rows: List[Dict[str, str]]) -> None:
    if not rows:
        raise ValueError("CSV sin registros")
    cols = set(rows[0].keys())
    faltan = [c for c in COLUMNAS_BASE_OBLIGATORIAS if c not in cols]

    tipos = {parse_int(row.get("TIPO_DOC")) for row in rows}
    if 61 in tipos:
        faltan.extend(c for c in COLUMNAS_NC_OBLIGATORIAS if c not in cols)
    if 33 in tipos:
        faltan.extend(c for c in COLUMNAS_FACTURA_OBLIGATORIAS if c not in cols)

    faltan = list(dict.fromkeys(faltan))
    if faltan:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(faltan))


def fw_text(valor: Any, largo: int) -> str:
    return texto_latin1(valor)[:largo].ljust(largo)


def fw_num(valor: Any, largo: int) -> str:
    if valor is None or valor == "":
        return "0" * largo
    try:
        n = int(round(float(valor)))
    except Exception:
        n = 0
    return str(n)[-largo:].zfill(largo)


def fw_decimal(valor: Any, largo: int, decimales: int) -> str:
    try:
        n = int(round(float(valor) * (10 ** decimales)))
    except Exception:
        n = 0
    return str(n)[-largo:].zfill(largo)


def linea(largo: int) -> List[str]:
    return list(" " * largo)


def put(buf: List[str], ini: int, fin: int, valor: str) -> None:
    largo = fin - ini + 1
    v = str(valor)
    if len(v) < largo:
        v = v.ljust(largo)
    elif len(v) > largo:
        v = v[:largo]
    buf[ini - 1:fin] = list(v)


def datos_emisor(rut_emisor: str) -> Dict[str, str]:
    if rut_emisor == RUT_CONDOR:
        return {
            "razon": "VTR Comunicaciones SpA",
            "giro": "Telecomunicaciones",
            "acteco": "64202",
            "direccion": "Avda. El Salto 5450",
            "comuna": "Huechuraba",
            "ciudad": "Santiago",
            "resol": "104",
        }
    return {
        "razon": "Claro Comunicaciones SpA",
        "giro": "Telecomunicaciones",
        "acteco": "64202",
        "direccion": "Avda. El Salto 5450",
        "comuna": "Huechuraba",
        "ciudad": "Santiago",
        "resol": "104",
    }
