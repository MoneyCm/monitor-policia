import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sisc_heartbeat import build_payload, send_heartbeat


class PoliceHeartbeatTests(unittest.TestCase):
    def test_builds_valid_payload_from_processed_status(self):
        status_path = Path.cwd() / ".test-police-source-status.json"
        self.addCleanup(status_path.unlink, missing_ok=True)
        status_path.write_text(
            json.dumps(
                {
                    "source_cutoff_date": "2026-06-30",
                    "period_label": "Corte al 2026-06-30 - 16 indicadores",
                    "record_count": 1055,
                    "indicator_count": 16,
                    "current_year": 2026,
                    "previous_year": 2025,
                }
            ),
            encoding="utf-8",
        )
        payload = build_payload(
            status_path,
            data_changed=True,
            now=datetime(2026, 8, 12, 12, 29, tzinfo=timezone.utc),
        )

        self.assertEqual(payload["connector_code"], "POLICIA_NACIONAL")
        self.assertEqual(payload["status"], "CURRENT")
        self.assertEqual(payload["source_cutoff_date"], "2026-06-30")
        self.assertEqual(payload["record_count"], 1055)
        self.assertIn("last_change_detected_at", payload)

    def test_failure_and_missing_identity_fail_closed(self):
        payload = build_payload(outcome="failure")
        self.assertEqual(payload["status"], "ERROR")
        self.assertFalse(send_heartbeat(payload, service_key="", oidc_token=""))


if __name__ == "__main__":
    unittest.main()
