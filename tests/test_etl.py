import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "etl_emision_dte_onlinegeneration_real.py"
spec = importlib.util.spec_from_file_location("etl_dte", MODULE_PATH)
etl = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = etl
spec.loader.exec_module(etl)


class TestParseo(unittest.TestCase):
    def test_parse_int_excel(self):
        self.assertEqual(etl.parse_int("39.0"), 39)
        self.assertEqual(etl.parse_int("121.189.675"), 121189675)
        self.assertIsNone(etl.parse_int("39.5"))

    def test_parse_monto_chileno(self):
        self.assertEqual(etl.parse_monto("23.000"), 23000)
        self.assertEqual(etl.parse_monto("23,000"), 23000)
        self.assertEqual(etl.parse_monto("23.000,00"), 23000)

    def test_fecha(self):
        self.assertEqual(etl.parse_fecha_yyyymmdd("2026-05-04T00:00"), "20260504")
        self.assertEqual(etl.parse_fecha_yyyymmdd("04/05/2026"), "20260504")


class TestReglaFechaNC(unittest.TestCase):
    def test_mes_actual_y_anterior(self):
        self.assertEqual(etl.validar_mes_referencia_nc("20260701", "20260728", 1), (True, 0))
        self.assertEqual(etl.validar_mes_referencia_nc("20260630", "20260728", 1), (True, 1))
        self.assertEqual(etl.validar_mes_referencia_nc("20260531", "20260728", 1), (False, 2))
        self.assertEqual(etl.validar_mes_referencia_nc("20260801", "20260728", 1), (False, -1))


class TestRespuesta(unittest.TestCase):
    def test_soap_cdata(self):
        raw = """<soap:Envelope xmlns:soap='http://www.w3.org/2003/05/soap-envelope'><soap:Body><return><![CDATA[<Respuesta><Codigo>0</Codigo><Mensaje>123456|http://ejemplo/pdf</Mensaje></Respuesta>]]></return></soap:Body></soap:Envelope>"""
        respuesta = etl.parsear_respuesta_ws(raw)
        self.assertEqual(respuesta.estado, "EMITIDO_OK")
        self.assertEqual(respuesta.folio_dte, "123456")
        self.assertEqual(respuesta.url_pdf, "http://ejemplo/pdf")


class TestB1(unittest.TestCase):
    def row_base(self, tipo_doc="39"):
        return {
            "MARCA": "PRUEBA", "RUT_EMISOR": "94675000-K", "TIPO_DOC": tipo_doc,
            "TIPO_SUSCRIPTOR": "Fijo", "RUT_CLIENTE": "11111111-1",
            "NOMBRE": "CLIENTE PRUEBA", "GIRO": "SERVICIOS", "DIRECCION": "CALLE 1",
            "COMUNA": "SANTIAGO", "CIUDAD": "SANTIAGO", "BILL_NO": "B1-TEST",
            "EMISION": "2026-07-28", "MONTO_DOC": "23.000", "EMAIL": "test@example.com",
            "TIPO_DOC_REF": "", "FOLIO_REBAJADO": "", "EMISION_BOLETA": "", "MONTO_NCRD": "",
        }

    def test_boleta_39(self):
        payload, errores = etl.construir_payload(self.row_base("39"), fecha_ejecucion=datetime(2026, 7, 28))
        self.assertEqual(errores, [])
        self.assertEqual(payload["TIPO_DTE"], 39)
        self.assertEqual(payload["MONTO_TOTAL_DTE"], 23000)
        args3 = etl.construir_args3(payload, 1)
        self.assertEqual([len(x) for x in args3.splitlines()], [1405, 2075, 123, 70])
        self.assertEqual(args3.splitlines()[0][1:4], "039")

    def test_factura_33_exige_giro(self):
        row = self.row_base("33")
        row["GIRO"] = ""
        _, errores = etl.construir_payload(row, fecha_ejecucion=datetime(2026, 7, 28))
        self.assertIn("GIRO vacío para factura DTE 33", errores)


class TestNC(unittest.TestCase):
    def row_nc(self, fecha_ref="2026-06-15"):
        return {
            "MARCA": "PRUEBA", "RUT_EMISOR": "76114143-0", "TIPO_DOC": "61",
            "TIPO_SUSCRIPTOR": "Fijo", "RUT_CLIENTE": "11111111-1",
            "NOMBRE": "CLIENTE PRUEBA", "GIRO": "", "DIRECCION": "CALLE 1",
            "COMUNA": "SANTIAGO", "CIUDAD": "SANTIAGO", "BILL_NO": "CB1-TEST",
            "EMISION": "2026-07-28", "MONTO_DOC": "49.527", "EMAIL": "test@example.com",
            "TIPO_DOC_REF": "39", "FOLIO_REBAJADO": "100000001",
            "EMISION_BOLETA": fecha_ref, "MONTO_NCRD": "23.000",
        }

    def test_nc_mes_anterior(self):
        payload, errores = etl.construir_payload(
            self.row_nc(), meses_referencia_nc=1, fecha_ejecucion=datetime(2026, 7, 28)
        )
        self.assertEqual(errores, [])
        self.assertEqual(payload["TIPO_DTE"], 61)
        self.assertEqual(payload["COD_REF"], 3)
        args3 = etl.construir_args3(payload, 1)
        self.assertEqual([len(x) for x in args3.splitlines()], [1405, 2075, 185, 123, 70])
        self.assertEqual(args3.splitlines()[2][34:42], "20260615")

    def test_nc_fuera_de_rango(self):
        _, errores = etl.construir_payload(
            self.row_nc("2026-05-31"), meses_referencia_nc=1,
            fecha_ejecucion=datetime(2026, 7, 28),
        )
        self.assertTrue(any("fuera del rango permitido" in error for error in errores))


if __name__ == "__main__":
    unittest.main()
