import unittest

import pandas as pd

from generar_reporte_policia import _crime_label, _jamundi_dane_mask


class OfficialReportParsingTests(unittest.TestCase):
    def test_maps_priority_crimes_without_accents_dependency(self):
        self.assertEqual(
            _crime_label("ARTICULO 239. HURTO PERSONAS"),
            "Hurto a personas",
        )
        self.assertEqual(
            _crime_label("ARTICULO 109. HOMICIDIO CULPOSO (EN ACCIDENTE DE TRANSITO)"),
            "Homicidios en transito",
        )
        self.assertEqual(
            _crime_label("ARTICULO 103. HOMICIDIO"),
            "Homicidios",
        )
        self.assertEqual(
            _crime_label("ARTICULO 208. ACCESO CARNAL ABUSIVO CON MENOR DE 14 ANOS"),
            "Delitos sexuales",
        )

    def test_normalizes_five_and_eight_digit_dane_codes(self):
        mask = _jamundi_dane_mask(pd.Series([76364, 76364000, 76001, None]))

        self.assertEqual(mask.tolist(), [True, True, False, False])


if __name__ == "__main__":
    unittest.main()
