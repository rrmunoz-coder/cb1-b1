from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from etl_common import (
    EMAIL_RE,
    GLOSA_B1_DEFAULT,
    GLOSA_NC_DEFAULT,
    IVA,
    RUT_ACEPTA,
    RUT_CONDOR,
    TIPOS_DTE_SOPORTADOS,
    datos_emisor,
    fw_decimal,
    fw_num,
    fw_text,
    linea,
    normalizar_rut,
    parse_fecha_yyyymmdd,
    parse_int,
    parse_monto,
    put,
    split_rut,
    texto,
    texto_latin1,
    validar_mes_referencia_nc,
)


def construir_payload(
    row: Dict[str, str],
    meses_referencia_nc: int = 1,
    fecha_ejecucion: Optional[datetime] = None,
    glosa_b1: str = GLOSA_B1_DEFAULT,
    glosa_nc: str = GLOSA_NC_DEFAULT,
) -> Tuple[Dict[str, Any], List[str]]:
    """Valida una fila y construye un payload DTE 33, 39 o 61.

    Contrato v2:
    - TIPO_DOC es siempre el DTE que se emitirá.
    - TIPO_DOC_REF sólo aplica a TIPO_DOC=61.
    - Para 33/39, MONTO_DOC es el total emitido.
    - Para 61, MONTO_NCRD es el total emitido y MONTO_DOC es el total original.
    """
    errores: List[str] = []
    ahora = fecha_ejecucion or datetime.now()
    fecha_ejecucion_yyyymmdd = ahora.strftime("%Y%m%d")

    rut_emisor = normalizar_rut(row.get("RUT_EMISOR"))
    rut_receptor = normalizar_rut(row.get("RUT_CLIENTE"))
    tipo_dte = parse_int(row.get("TIPO_DOC"))
    tipo_ref = parse_int(row.get("TIPO_DOC_REF")) if tipo_dte == 61 else None
    bill_no = texto(row.get("BILL_NO"))
    email = texto(row.get("EMAIL"))
    fecha_origen_csv = parse_fecha_yyyymmdd(row.get("EMISION"))
    monto_doc = parse_monto(row.get("MONTO_DOC"))
    monto_nc = parse_monto(row.get("MONTO_NCRD")) if tipo_dte == 61 else None

    if rut_emisor == RUT_ACEPTA:
        motor = "ACEPTA"
    elif rut_emisor == RUT_CONDOR:
        motor = "CONDOR"
    else:
        motor = "ERROR"
        errores.append(f"RUT_EMISOR no soportado: {rut_emisor}")

    if tipo_dte not in TIPOS_DTE_SOPORTADOS:
        errores.append(f"TIPO_DOC inválido: {tipo_dte}; debe ser 33, 39 o 61")
    if not bill_no:
        errores.append("BILL_NO vacío")
    if not rut_receptor:
        errores.append("RUT_CLIENTE vacío")
    if not texto(row.get("NOMBRE")):
        errores.append("NOMBRE vacío")
    if not texto(row.get("DIRECCION")):
        errores.append("DIRECCION vacía")
    if not texto(row.get("COMUNA")):
        errores.append("COMUNA vacía")
    if not texto(row.get("CIUDAD")):
        errores.append("CIUDAD vacía")
    if email and not EMAIL_RE.match(email):
        errores.append(f"EMAIL inválido: {email}")
    if monto_doc is None or monto_doc <= 0:
        errores.append("MONTO_DOC inválido o <= 0")

    folio_ref = None
    folio_ref_txt = ""
    fecha_ref = None
    cod_ref = None

    if tipo_dte in (33, 39):
        if fecha_origen_csv is None:
            errores.append("EMISION inválida para B1")
            fecha_dte = fecha_ejecucion_yyyymmdd
        else:
            fecha_dte = fecha_origen_csv
            if fecha_dte > fecha_ejecucion_yyyymmdd:
                errores.append("EMISION futura; no emitir B1")
        if tipo_dte == 33 and not texto(row.get("GIRO")):
            errores.append("GIRO vacío para factura DTE 33")
        monto_total_dte = monto_doc
        glosa = texto_latin1(glosa_b1) or GLOSA_B1_DEFAULT
    else:
        fecha_dte = fecha_ejecucion_yyyymmdd
        folio_ref = parse_int(row.get("FOLIO_REBAJADO"))
        folio_ref_txt = str(folio_ref) if folio_ref is not None else texto(row.get("FOLIO_REBAJADO"))
        fecha_ref = parse_fecha_yyyymmdd(row.get("EMISION_BOLETA"))

        if tipo_ref not in (33, 39, 61):
            errores.append(f"TIPO_DOC_REF inválido: {tipo_ref}; debe ser 33, 39 o 61")
        if folio_ref is None:
            errores.append("FOLIO_REBAJADO inválido")
        if fecha_ref is None:
            errores.append("EMISION_BOLETA inválida")
        else:
            fecha_valida, diferencia = validar_mes_referencia_nc(
                fecha_ref,
                fecha_dte,
                meses_referencia_nc,
            )
            if not fecha_valida:
                if diferencia < 0:
                    errores.append("EMISION_BOLETA pertenece a un mes futuro; no emitir NC")
                else:
                    errores.append(
                        "EMISION_BOLETA fuera del rango permitido: "
                        f"antigüedad={diferencia} meses; máximo={meses_referencia_nc}"
                    )
        if monto_nc is None or monto_nc <= 0:
            errores.append("MONTO_NCRD inválido o <= 0")
        if monto_nc is not None and monto_doc is not None and monto_nc > monto_doc:
            errores.append("MONTO_NCRD > MONTO_DOC; no emitir")

        cod_ref = 1 if monto_nc is not None and monto_doc is not None and monto_nc == monto_doc else 3
        monto_total_dte = monto_nc
        glosa = texto_latin1(glosa_nc) or GLOSA_NC_DEFAULT

    neto = None
    iva = None
    if monto_total_dte is not None and monto_total_dte > 0:
        neto = int(round(monto_total_dte / (1 + IVA)))
        iva = monto_total_dte - neto

    payload = {
        "MOTOR": motor,
        "BILL_NO": bill_no,
        "MARCA": texto_latin1(row.get("MARCA")),
        "TIPO_SUSCRIPTOR": texto_latin1(row.get("TIPO_SUSCRIPTOR")),
        "RUT_EMISOR": rut_emisor,
        "RUT_RECEPTOR": rut_receptor,
        "TIPO_DTE": tipo_dte,
        "TIPO_DOC_REF": tipo_ref,
        "FOLIO_REF": folio_ref,
        "FOLIO_REF_TXT": folio_ref_txt,
        "FECHA_DTE": fecha_dte,
        "FECHA_ORIGEN_CSV": fecha_origen_csv,
        "FECHA_DOC_REF": fecha_ref,
        "MESES_REFERENCIA_NC": meses_referencia_nc,
        "MONTO_DOC": monto_doc,
        "MONTO_NC": monto_nc,
        "MONTO_TOTAL_DTE": monto_total_dte,
        "MONTO_NETO": neto,
        "MONTO_IVA": iva,
        "COD_REF": cod_ref,
        "GLOSA": glosa,
        "RAZON_SOCIAL": texto_latin1(row.get("NOMBRE")),
        "GIRO_RECEPTOR": texto_latin1(row.get("GIRO")) or ".",
        "DIRECCION": texto_latin1(row.get("DIRECCION")),
        "COMUNA": texto_latin1(row.get("COMUNA")),
        "CIUDAD": texto_latin1(row.get("CIUDAD")),
        "EMAIL": email,
    }
    return payload, errores


def construir_args3(payload: Dict[str, Any], folio_interno: int, tipo_foliacion_e72: str = "2") -> str:
    """Construye E/D/G/T para B1 y E/D/F/G/T para NC."""
    rut_e, dv_e = split_rut(payload["RUT_EMISOR"])
    rut_r, dv_r = split_rut(payload["RUT_RECEPTOR"])
    emisor = datos_emisor(payload["RUT_EMISOR"])

    E = linea(1405)
    put(E, 1, 1, "E")
    put(E, 2, 4, fw_num(payload["TIPO_DTE"], 3))
    put(E, 5, 14, fw_num(folio_interno, 10))
    put(E, 15, 22, payload["FECHA_DTE"])
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
    put(E, 602, 641, fw_text(payload["GIRO_RECEPTOR"], 40))
    put(E, 722, 781, fw_text(payload["DIRECCION"], 60))
    put(E, 782, 801, fw_text(payload["COMUNA"], 20))
    put(E, 817, 876, fw_text(payload["CIUDAD"], 60))
    put(E, 1033, 1050, fw_num(payload["MONTO_NETO"], 18))
    put(E, 1051, 1068, fw_num(0, 18))
    put(E, 1087, 1091, "01900")
    put(E, 1092, 1109, fw_num(payload["MONTO_IVA"], 18))
    put(E, 1164, 1181, fw_num(payload["MONTO_TOTAL_DTE"], 18))
    put(E, 1338, 1338, "1")
    put(E, 1339, 1339, "A")
    put(E, 1340, 1340, str(tipo_foliacion_e72)[:1])
    put(E, 1385, 1404, fw_text(payload["BILL_NO"], 20))

    D = linea(2075)
    put(D, 1, 1, "D")
    put(D, 2, 5, fw_num(1, 4))
    put(D, 6, 9, fw_num(1, 4))
    put(D, 215, 215, "0")
    put(D, 216, 295, fw_text(payload["GLOSA"], 80))
    put(D, 336, 353, fw_decimal(1, 18, 6))
    put(D, 635, 638, fw_text("UN", 4))
    put(D, 639, 656, fw_decimal(payload["MONTO_NETO"], 18, 6))
    put(D, 945, 962, fw_num(payload["MONTO_NETO"], 18))
    put(D, 963, 1962, fw_text(payload["GLOSA"], 1000))

    registros = ["".join(E), "".join(D)]

    if payload["TIPO_DTE"] == 61:
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
        put(F, 44, 73, fw_text(payload["GLOSA"], 30))
        put(F, 84, 173, fw_text(payload["GLOSA"], 90))
        registros.append("".join(F))

    G = linea(123)
    put(G, 1, 1, "G")
    put(G, 2, 3, fw_num(1, 2))
    put(G, 4, 23, fw_text("GNUMDOC", 20))
    put(G, 24, 123, fw_text(payload["BILL_NO"], 100))
    registros.append("".join(G))

    T = linea(70)
    put(T, 1, 1, "T")
    put(T, 2, 11, fw_num(folio_interno, 10))
    put(T, 12, 21, fw_num(folio_interno, 10))
    put(T, 22, 31, fw_num(1, 10))
    registros.append("".join(T))

    return "\n".join(registros)
