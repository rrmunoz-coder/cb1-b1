from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from etl_common import (
    EMAIL_RE, GLOSA_NC, IVA, RUT_ACEPTA, RUT_CONDOR, TIPO_DTE_NC,
    datos_emisor, fw_decimal, fw_num, fw_text, linea, normalizar_rut,
    parse_fecha_yyyymmdd, parse_int, parse_monto, put, split_rut, texto,
    texto_latin1,
)

def construir_payload(row: Dict[str, str], tipo_doc_default: Optional[int] = None) -> Tuple[Dict[str, Any], List[str]]:
    errores: List[str] = []
    rut_emisor = normalizar_rut(row.get("RUT_EMISOR"))
    rut_receptor = normalizar_rut(row.get("RUT_CLIENTE"))
    tipo_dte = parse_int(row.get("TIPO_DOC_TRIB"))
    tipo_ref = parse_int(row.get("TIPO_DOC")) if "TIPO_DOC" in row else tipo_doc_default
    folio_ref_txt = texto(row.get("FOLIO_REBAJADO")).replace(".0", "").strip()
    folio_ref = parse_int(row.get("FOLIO_REBAJADO"))
    fecha_nc = datetime.now().strftime("%Y%m%d")
    fecha_origen_csv = parse_fecha_yyyymmdd(row.get("EMISION"))
    fecha_ref = parse_fecha_yyyymmdd(row.get("EMISION_BOLETA"))
    monto_nc = parse_monto(row.get("MONTO_NCRD"))
    monto_doc = parse_monto(row.get("MONTO_DOC"))
    bill_no = texto(row.get("BILL_NO"))
    email = texto(row.get("EMAIL"))

    if rut_emisor == RUT_ACEPTA:
        motor = "ACEPTA"
    elif rut_emisor == RUT_CONDOR:
        motor = "CONDOR"
    else:
        motor = "ERROR"
        errores.append(f"RUT_EMISOR no soportado: {rut_emisor}")

    if tipo_dte != TIPO_DTE_NC:
        errores.append(f"TIPO_DOC_TRIB inválido: {tipo_dte}; debe ser 61")
    if tipo_ref not in (33, 39, 61):
        errores.append(f"TIPO_DOC referencia inválido: {tipo_ref}")
    if not bill_no:
        errores.append("BILL_NO vacío")
    if not rut_receptor:
        errores.append("RUT_CLIENTE vacío")
    if folio_ref is None:
        errores.append("FOLIO_REBAJADO inválido")
    if fecha_ref is None:
        errores.append("EMISION_BOLETA inválida")
    if monto_nc is None or monto_nc <= 0:
        errores.append("MONTO_NCRD inválido o <= 0")
    if monto_doc is None or monto_doc <= 0:
        errores.append("MONTO_DOC inválido o <= 0")
    if monto_nc is not None and monto_doc is not None and monto_nc > monto_doc:
        errores.append("MONTO_NCRD > MONTO_DOC; no emitir")
    if email and not EMAIL_RE.match(email):
        errores.append(f"EMAIL inválido: {email}")

    cod_ref = None
    neto = None
    iva = None
    if monto_nc is not None and monto_doc is not None:
        cod_ref = 1 if monto_nc == monto_doc else 3
        neto = int(round(monto_nc / (1 + IVA)))
        iva = monto_nc - neto

    payload = {
        "MOTOR": motor,
        "BILL_NO": bill_no,
        "MARCA": texto_latin1(row.get("MARCA")),
        "TIPO_SUSCRIPTOR": texto_latin1(row.get("TIPO_SUSCRIPTOR")),
        "RUT_EMISOR": rut_emisor,
        "RUT_RECEPTOR": rut_receptor,
        "TIPO_DTE": TIPO_DTE_NC,
        "TIPO_DOC_REF": tipo_ref,
        "FOLIO_REF": folio_ref,
        "FOLIO_REF_TXT": folio_ref_txt,
        "FECHA_NC": fecha_nc,
        "FECHA_ORIGEN_CSV": fecha_origen_csv,
        "FECHA_DOC_REF": fecha_ref,
        "MONTO_DOC": monto_doc,
        "MONTO_NC": monto_nc,
        "MONTO_NETO": neto,
        "MONTO_IVA": iva,
        "COD_REF": cod_ref,
        "RAZON_SOCIAL": texto_latin1(row.get("NOMBRE")),
        "DIRECCION": texto_latin1(row.get("DIRECCION")),
        "COMUNA": texto_latin1(row.get("COMUNA")),
        "CIUDAD": texto_latin1(row.get("CIUDAD")),
        "EMAIL": email,
    }
    return payload, errores

def construir_args3(payload: Dict[str, Any], folio_interno: int, tipo_foliacion_e72: str = "2") -> str:
    """Construye args3 posicional: E, D, F, G, T según plantilla Paperless/SAP."""
    rut_e, dv_e = split_rut(payload["RUT_EMISOR"])
    rut_r, dv_r = split_rut(payload["RUT_RECEPTOR"])
    emisor = datos_emisor(payload["RUT_EMISOR"])

    E = linea(1405)
    put(E, 1, 1, "E")
    put(E, 2, 4, fw_num(61, 3))
    put(E, 5, 14, fw_num(folio_interno, 10))
    put(E, 15, 22, payload["FECHA_NC"])
    put(E, 23, 23, "0")
    put(E, 26, 26, "0")
    put(E, 28, 28, "2")
    put(E, 70, 77, fw_num(rut_e, 8))
    put(E, 78, 78, dv_e)
    put(E, 79, 84, fw_num(emisor["resol"], 6))
    put(E, 85, 184, fw_text(emisor["razon"], 100))
    put(E, 185, 264, fw_text(emisor["giro"], 80))
    put(E, 265, 269, fw_num(emisor["acteco"], 5))
    put(E, 309, 368, fw_text(emisor["direccion"], 60))
    put(E, 369, 388, fw_text(emisor["comuna"], 20))
    put(E, 389, 403, fw_text(emisor["ciudad"], 15))
    put(E, 473, 480, fw_num(rut_r, 8))
    put(E, 481, 481, dv_r)
    put(E, 502, 601, fw_text(payload["RAZON_SOCIAL"], 100))
    put(E, 602, 641, fw_text(".", 40))
    put(E, 722, 781, fw_text(payload["DIRECCION"], 60))
    put(E, 782, 801, fw_text(payload["COMUNA"], 20))
    put(E, 817, 876, fw_text(payload["CIUDAD"], 60))
    put(E, 1033, 1050, fw_num(payload["MONTO_NETO"], 18))
    put(E, 1051, 1068, fw_num(0, 18))
    put(E, 1087, 1091, "01900")
    put(E, 1092, 1109, fw_num(payload["MONTO_IVA"], 18))
    put(E, 1164, 1181, fw_num(payload["MONTO_NC"], 18))
    put(E, 1338, 1338, "1")
    put(E, 1339, 1339, "A")
    put(E, 1340, 1340, str(tipo_foliacion_e72)[:1])
    put(E, 1385, 1404, fw_text(payload["BILL_NO"], 20))

    D = linea(2075)
    put(D, 1, 1, "D")
    put(D, 2, 5, fw_num(1, 4))
    put(D, 6, 9, fw_num(1, 4))
    put(D, 215, 215, "0")
    put(D, 216, 295, fw_text(GLOSA_NC, 80))
    put(D, 336, 353, fw_decimal(1, 18, 6))
    put(D, 635, 638, fw_text("UN", 4))
    put(D, 639, 656, fw_decimal(payload["MONTO_NETO"], 18, 6))
    put(D, 945, 962, fw_num(payload["MONTO_NETO"], 18))
    put(D, 963, 1962, fw_text(GLOSA_NC, 1000))

    F = linea(185)
    put(F, 1, 1, "F")
    put(F, 2, 3, fw_num(1, 2))
    if payload.get("MOTOR") == "ACEPTA":
        put(F, 4, 6, fw_text(str(payload["TIPO_DOC_REF"]), 3))
    else:
        put(F, 4, 6, fw_num(payload["TIPO_DOC_REF"], 3))
    put(F, 7, 7, "0")

    folio_ref_txt = texto(payload.get("FOLIO_REF_TXT") or payload.get("FOLIO_REF"))
    if len(folio_ref_txt) <= 18:
        put(F, 8, 25, fw_text(folio_ref_txt, 18))
    else:
        put(F, 8, 25, fw_text("0", 18))
        put(F, 167, 185, fw_text(folio_ref_txt, 19))

    put(F, 26, 33, fw_num(0, 8))
    put(F, 34, 34, " ")
    put(F, 35, 42, payload["FECHA_DOC_REF"])
    put(F, 43, 43, str(payload["COD_REF"]))
    put(F, 44, 73, fw_text(GLOSA_NC, 30))
    put(F, 84, 173, fw_text(GLOSA_NC, 90))

    G = linea(123)
    put(G, 1, 1, "G")
    put(G, 2, 3, fw_num(1, 2))
    put(G, 4, 23, fw_text("GNUMDOC", 20))
    put(G, 24, 123, fw_text(payload["BILL_NO"], 100))

    T = linea(70)
    put(T, 1, 1, "T")
    put(T, 2, 11, fw_num(folio_interno, 10))
    put(T, 12, 21, fw_num(folio_interno, 10))
    put(T, 22, 31, fw_num(1, 10))

    return "\n".join(["".join(E), "".join(D), "".join(F), "".join(G), "".join(T)])
