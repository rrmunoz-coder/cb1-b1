import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "etl_emision_nc_onlinegeneration_real.py"
spec = importlib.util.spec_from_file_location("etl_nc", MODULE_PATH)
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
        self.assertEqual(etl.parse_monto("23000"), 23000)

    def test_fecha(self):
        self.assertEqual(etl.parse_fecha_yyyymmdd("2026-05-04T00:00"), "20260504")
        self.assertEqual(etl.parse_fecha_yyyymmdd("04/05/2026"), "20260504")


class TestRespuesta(unittest.TestCase):
    def test_soap_cdata(self):
        raw = """<soap:Envelope xmlns:soap='http://www.w3.org/2003/05/soap-envelope'><soap:Body><return><![CDATA[<Respuesta><Codigo>0</Codigo><Mensaje>123456|http://ejemplo/pdf</Mensaje></Respuesta>]]></return></soap:Body></soap:Envelope>"""
        r = etl.parsear_respuesta_ws(raw)
        self.assertEqual(r.estado, "EMITIDO_OK")
        self.assertEqual(r.folio_nc, "123456")
        self.assertEqual(r.url_pdf, "http://ejemplo/pdf")


class TestPayload(unittest.TestCase):
    def test_args3_largos(self):
        row = {
            "MARCA": "PRUEBA", "RUT_EMISOR": "94675000-K", "TIPO_DOC_TRIB": "61",
            "TIPO_DOC": "39.0", "TIPO_SUSCRIPTOR": "Fijo", "RUT_CLIENTE": "11111111-1",
            "NOMBRE": "CLIENTE PRUEBA", "DIRECCION": "CALLE 1", "COMUNA": "SANTIAGO",
            "CIUDAD": "SANTIAGO", "BILL_NO": "CB1-TEST", "EMISION": "2026-07-28",
            "FOLIO_REBAJADO": "100000001", "EMISION_BOLETA": "2026-07-01",
            "MONTO_NCRD": "23.000", "MONTO_DOC": "49.527", "EMAIL": "test@example.com",
        }
        payload, errores = etl.construir_payload(row)
        self.assertEqual(errores, [])
        args3 = etl.construir_args3(payload, 1)
        self.assertEqual([len(x) for x in args3.splitlines()], [1405, 2075, 185, 123, 70])


if __name__ == "__main__":
    unittest.main()
