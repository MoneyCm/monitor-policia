import unittest
from datetime import datetime
from unittest.mock import Mock

from official_policia_source import (
    calculate_fingerprint,
    discover_record_files,
    fetch_record_files,
)


class OfficialPoliciaSourceTests(unittest.TestCase):
    HTML = """
    <a href="/files/registro_2025.xlsx">Informacion de delitos a nivel de registro ano 2025</a>
    <a href="/files/registro_2026.xlsx">Informacion de delitos a nivel de registro ano 2026</a>
    <a href="/files/resumen.xlsx">Cuadro de salida delictivo</a>
    """

    def test_discovers_only_yearly_record_files(self):
        files = discover_record_files(self.HTML, "https://example.test/page")

        self.assertEqual(files[2025], "https://example.test/files/registro_2025.xlsx")
        self.assertEqual(files[2026], "https://example.test/files/registro_2026.xlsx")
        self.assertEqual(len(files), 2)

    def test_fetch_requires_current_and_previous_year(self):
        response = Mock(text=self.HTML)
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        files = fetch_record_files(session=session, now=datetime(2026, 8, 12))

        self.assertEqual(set(files), {2025, 2026})

    def test_fingerprint_is_deterministic(self):
        session = Mock()
        response = Mock(status_code=200, url="https://example.test/file.xlsx")
        response.headers = {
            "ETag": '"abc"',
            "Content-Range": "bytes 0-7/42",
        }
        response.raise_for_status.return_value = None
        response.iter_content.return_value = [b"PKsample"]
        session.get.return_value = response
        first, _ = calculate_fingerprint({2026: response.url}, session=session)
        second, _ = calculate_fingerprint({2026: response.url}, session=session)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
