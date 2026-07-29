from __future__ import annotations

import configparser
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from etl_main import aplicar_defaults_ini  # noqa: E402


class TestDefaultsIni(unittest.TestCase):
    def config(self) -> configparser.ConfigParser:
        cfg = configparser.ConfigParser()
        cfg.read_dict({
            "VALORES_POR_DEFECTO": {
                "nombre": "CLIENTE DEFAULT",
                "giro": "TELECOMUNICACIONES",
                "direccion": "AV. PRUEBA 123",
                "comuna": "SANTIAGO",
                "ciudad": "SANTIAGO",
                "email": "default@example.com",
                "monto_doc": "999999",
            }
        })
        return cfg

    def test_completa_solo_campos_vacios(self):
        row = {
            "NOMBRE": "",
            "GIRO": "GIRO DEL CSV",
            "DIRECCION": "",
            "COMUNA": "COMUNA CSV",
            "CIUDAD": "",
            "EMAIL": "",
            "MONTO_DOC": "25000",
        }
        resultado, usados = aplicar_defaults_ini(row, self.config())

        self.assertEqual("CLIENTE DEFAULT", resultado["NOMBRE"])
        self.assertEqual("GIRO DEL CSV", resultado["GIRO"])
        self.assertEqual("AV. PRUEBA 123", resultado["DIRECCION"])
        self.assertEqual("COMUNA CSV", resultado["COMUNA"])
        self.assertEqual("SANTIAGO", resultado["CIUDAD"])
        self.assertEqual("default@example.com", resultado["EMAIL"])
        self.assertEqual("25000", resultado["MONTO_DOC"])
        self.assertEqual(["NOMBRE", "DIRECCION", "CIUDAD", "EMAIL"], usados)

    def test_no_sobreescribe_valores_del_csv(self):
        row = {
            "NOMBRE": "CLIENTE ORACLE",
            "GIRO": "GIRO ORACLE",
            "DIRECCION": "DIRECCION ORACLE",
            "COMUNA": "COMUNA ORACLE",
            "CIUDAD": "CIUDAD ORACLE",
            "EMAIL": "oracle@example.com",
        }
        resultado, usados = aplicar_defaults_ini(row, self.config())

        self.assertEqual(row, resultado)
        self.assertEqual([], usados)

    def test_sin_seccion_no_modifica_fila(self):
        cfg = configparser.ConfigParser()
        row = {"NOMBRE": "", "DIRECCION": ""}
        resultado, usados = aplicar_defaults_ini(row, cfg)

        self.assertEqual(row, resultado)
        self.assertEqual([], usados)

    def test_no_aplica_defaults_financieros(self):
        row = {"MONTO_DOC": ""}
        resultado, usados = aplicar_defaults_ini(row, self.config())

        self.assertEqual("", resultado["MONTO_DOC"])
        self.assertEqual([], usados)


if __name__ == "__main__":
    unittest.main()
