from __future__ import annotations

import configparser
import html
import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

try:
    import requests
except ImportError as exc:
    raise SystemExit("Falta librería requests. Instala con: pip install requests") from exc

from etl_common import DEFAULT_ENDPOINT, SOAP_NS, WEB_NS, RespuestaWS, split_rut


def construir_soap(args0: str, args1: str, args2: str, args3: str, args4: str, args5: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="{SOAP_NS}" xmlns:web="{WEB_NS}">
   <soap:Header/>
   <soap:Body>
      <web:OnlineGenerationDte>
         <web:args0>{html.escape(args0)}</web:args0>
         <web:args1>{html.escape(args1)}</web:args1>
         <web:args2>{html.escape(args2)}</web:args2>
         <web:args3>{html.escape(args3, quote=False)}</web:args3>
         <web:args4>{html.escape(args4)}</web:args4>
         <web:args5>{html.escape(args5)}</web:args5>
      </web:OnlineGenerationDte>
   </soap:Body>
</soap:Envelope>'''


def motor_section(motor: str) -> str:
    return "ACEPTA" if motor == "ACEPTA" else "CONDOR"


def extraer_texto_tag(xml_text: str, tag: str) -> str:
    if not xml_text:
        return ""
    try:
        root = ET.fromstring(xml_text.strip())
        for elem in root.iter():
            local = elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag
            if local == tag:
                return (elem.text or "").strip()
    except Exception:
        pass

    match = re.search(
        rf"<(?:(?:\w+):)?{re.escape(tag)}\b[^>]*>(.*?)</(?:(?:\w+):)?{re.escape(tag)}>",
        xml_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return html.unescape(match.group(1)).strip()
    return ""


def parsear_respuesta_ws(raw: str) -> RespuestaWS:
    contenido = raw or ""
    try:
        root = ET.fromstring(raw)
        for elem in root.iter():
            local = elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag
            if local == "return":
                contenido = elem.text or ""
                break
    except Exception:
        pass

    contenido = html.unescape((contenido or "").strip())
    codigo = extraer_texto_tag(contenido, "Codigo") or extraer_texto_tag(raw, "Codigo")
    mensaje = extraer_texto_tag(contenido, "Mensaje") or extraer_texto_tag(raw, "Mensaje")
    if not mensaje:
        mensaje = contenido.strip()

    folio = ""
    url = ""
    if codigo in ("0", "00"):
        if "|" in mensaje:
            folio, url = mensaje.split("|", 1)
            folio = folio.strip()
            url = url.strip()
        else:
            match = re.search(r"\b(\d{5,})\b", mensaje)
            if match:
                folio = match.group(1)

    estado = "EMITIDO_OK" if codigo in ("0", "00") and folio else "RESPUESTA_REVISAR"
    return RespuestaWS(estado=estado, folio_dte=folio, url_pdf=url, codigo=codigo, mensaje=mensaje, raw_response=raw)


def normalizar_respuesta_acepta(resp: RespuestaWS) -> RespuestaWS:
    fuente = resp.mensaje or resp.raw_response or ""
    mensaje = extraer_texto_tag(fuente, "Mensaje") or resp.mensaje or ""
    codigo = extraer_texto_tag(fuente, "Codigo") or resp.codigo or ""
    folio = resp.folio_dte or ""
    url = resp.url_pdf or ""

    if "|" in mensaje:
        partes = mensaje.split("|", 1)
        folio = folio or partes[0].strip()
        url = url or partes[1].strip()
    elif not folio:
        match = re.search(r"\b(\d{5,})\b", mensaje)
        if match:
            folio = match.group(1)

    estado = "EMITIDO_OK" if codigo in ("0", "00") and folio else resp.estado
    return RespuestaWS(
        estado=estado,
        folio_dte=folio,
        url_pdf=url,
        codigo=codigo,
        mensaje=mensaje.strip(),
        raw_response=resp.raw_response,
    )


def emitir_ws(payload: Dict[str, Any], args3: str, cfg: configparser.ConfigParser) -> RespuestaWS:
    sec = motor_section(payload["MOTOR"])
    endpoint = cfg.get("GENERAL", "endpoint", fallback=DEFAULT_ENDPOINT).strip()
    args0 = cfg.get(sec, "args0", fallback=split_rut(payload["RUT_EMISOR"])[0])
    args1 = cfg.get(sec, "args1", fallback="")
    args2 = cfg.get(sec, "args2", fallback="")
    args4 = cfg.get("GENERAL", "args4", fallback="1")
    args5 = cfg.get("GENERAL", "args5", fallback="2")
    timeout = cfg.getint("GENERAL", "timeout_segundos", fallback=60)
    reintentos = cfg.getint("GENERAL", "reintentos", fallback=1)
    pausa = cfg.getint("GENERAL", "pausa_reintento_segundos", fallback=3)

    if not endpoint or endpoint.upper().startswith("COMPLETAR"):
        raise RuntimeError("Config incompleta en [GENERAL]: completar endpoint")
    if not args1 or args1.upper().startswith("COMPLETAR") or not args2 or args2.upper().startswith("COMPLETAR"):
        raise RuntimeError(f"Config incompleta en [{sec}]: completar args1 y args2")

    soap = construir_soap(args0, args1, args2, args3, args4, args5)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
    ultimo_error: Optional[Exception] = None

    for intento in range(1, reintentos + 2):
        try:
            logging.info("Emitiendo motor=%s BILL_NO=%s intento=%s", payload["MOTOR"], payload["BILL_NO"], intento)
            response = requests.post(endpoint, data=soap.encode("utf-8"), headers=headers, timeout=timeout)
            if response.status_code >= 400:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:800]}")
            return parsear_respuesta_ws(response.text)
        except Exception as exc:
            ultimo_error = exc
            logging.warning("Fallo intento %s: %s", intento, exc)
            if intento <= reintentos:
                time.sleep(pausa)
    raise RuntimeError(str(ultimo_error))
