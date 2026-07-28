from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "extraer_candidatos_oracle.py"
SPEC = importlib.util.spec_from_file_location("extraer_candidatos_oracle", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class TestExtraccionOracle(unittest.TestCase):
    def fila_base(self):
        return {
            "MARCA": "CLARO",
            "RUT_EMISOR": "94675000-K",
            "TIPO_DOC": "39",
            "TIPO_SUSCRIPTOR": "Fijo",
            "RUT_CLIENTE": "11111111-1",
            "NOMBRE": "CLIENTE",
            "GIRO": "",
            "DIRECCION": "DIRECCION",
            "COMUNA": "SANTIAGO",
            "CIUDAD": "SANTIAGO",
            "BILL_NO": "B1-TEST",
            "EMISION": "2026-07-28",
            "MONTO_DOC": "23000",
            "EMAIL": "",
            "TIPO_DOC_REF": "",
            "FOLIO_REBAJADO": "",
            "EMISION_BOLETA": "",
            "MONTO_NCRD": "",
        }

    def test_contrato_tiene_18_columnas(self):
        self.assertEqual(18, len(MOD.COLUMNAS_ENTRADA))

    def test_b1_39_valido(self):
        self.assertEqual([], MOD.validar_fila(self.fila_base()))

    def test_factura_33_exige_giro(self):
        row = self.fila_base()
        row["TIPO_DOC"] = "33"
        self.assertIn("GIRO vacío para DTE 33", MOD.validar_fila(row))

    def test_nc_exige_referencia(self):
        row = self.fila_base()
        row["TIPO_DOC"] = "61"
        errores = MOD.validar_fila(row)
        self.assertTrue(any("FOLIO_REBAJADO" in e for e in errores))
        self.assertTrue(any("EMISION_BOLETA" in e for e in errores))
        self.assertTrue(any("MONTO_NCRD" in e for e in errores))

    def test_nc_valida_monto(self):
        row = self.fila_base()
        row.update({
            "TIPO_DOC": "61",
            "TIPO_DOC_REF": "39",
            "FOLIO_REBAJADO": "100",
            "EMISION_BOLETA": "2026-07-01",
            "MONTO_NCRD": "24000",
        })
        self.assertIn("MONTO_NCRD mayor que MONTO_DOC", MOD.validar_fila(row))

    def test_normaliza_fecha_oracle(self):
        self.assertEqual("2026-07-28", MOD.normalizar_salida(date(2026, 7, 28)))

    def test_booleanos_ini(self):
        self.assertTrue(MOD.es_verdadero("sí"))
        self.assertFalse(MOD.es_verdadero("false"))


if __name__ == "__main__":
    unittest.main()
