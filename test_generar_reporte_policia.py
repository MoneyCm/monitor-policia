import unittest

import pandas as pd

from generar_reporte_policia import _build_fecha_hecho, _crime_label, _jamundi_dane_mask


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

    def test_maps_2026_iccs_labels(self):
        cases = {
            "(05022) Hurto a personas": "Hurto a personas",
            "(050212) Hurto a motocicletas": "Hurto de motocicletas",
            "(050211) Hurto a automotores": "Hurto de automotores",
            "(05010) Hurto a residencias": "Hurto a residencias",
            "(05023) Hurto a comercio": "Hurto a comercio",
            "(02012) Amenaza": "Amenazas",
            "(0101) Homicidio intencional": "Homicidios",
            "(10321) Homicidio por tránsito vehicular (Homicidios en accidentes de tránsito)": "Homicidios en transito",
            "(02019) Otras formas de agresiones y amenazas (Lesiones culposas en accidentes de tránsito)": "Lesiones en transito",
            "(02089) Otros actos dirigidos a inducir miedo o angustia emocional (Violencia intrafamiliar)": "Violencia intrafamiliar",
        }
        for label, expected in cases.items():
            self.assertEqual(_crime_label(label), expected, label)

    def test_year_first_dates_keep_day_and_month(self):
        fechas = _build_fecha_hecho(pd.DataFrame({"FECHA HECHO": ["2025/01/05", "2025/01/13", "2025/12/12"]}))
        self.assertEqual([f.strftime("%Y-%m-%d") for f in fechas], ["2025-01-05", "2025-01-13", "2025-12-12"])

    def test_normalizes_five_and_eight_digit_dane_codes(self):
        mask = _jamundi_dane_mask(pd.Series([76364, 76364000, 76001, None]))

        self.assertEqual(mask.tolist(), [True, True, False, False])


if __name__ == "__main__":
    unittest.main()
