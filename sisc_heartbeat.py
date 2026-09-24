"""Report the Policia Nacional monitor status to the SISC source center."""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_API_URL = "https://sisc-backend.onrender.com/api"


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _iso_datetime(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _status_data(path: Optional[Path] = None) -> Dict[str, Any]:
    if path is not None:
        return _load_json(Path(path)) or {}
    for candidate in (
        BASE_DIR / "source_status.json",
        BASE_DIR / ".monitor_state" / "source_status.json",
    ):
        value = _load_json(candidate)
        if value:
            return value
    return {}


def _as_non_negative_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _parse_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def build_payload(
    status_path: Optional[Path] = None,
    *,
    outcome: str = "success",
    data_changed: bool = False,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    checked_at = _utc_now(now)
    workflow_ok = (outcome or "success").strip().lower() == "success"
    status_data = _status_data(status_path)
    cutoff = _parse_date(status_data.get("source_cutoff_date"))
    indicator_count = _as_non_negative_int(status_data.get("indicator_count"))
    record_count = _as_non_negative_int(status_data.get("record_count"))
    warnings = []

    if not workflow_ok:
        warnings.append("La revision diaria de Policia Nacional termino con error.")
    elif not status_data:
        warnings.append("La fuente fue revisada, pero aun no existe un corte procesado.")
    elif not cutoff:
        warnings.append("El procesamiento no informo una fecha de corte valida.")

    if not workflow_ok:
        status, quality = "ERROR", "ERROR"
    elif not cutoff:
        status, quality = "NEEDS_REVIEW", "INCOMPLETE"
    else:
        status, quality = "CURRENT", "VALIDATED"

    payload: Dict[str, Any] = {
        "connector_code": "POLICIA_NACIONAL",
        "status": status,
        "quality_status": quality,
        "last_checked_at": _iso_datetime(checked_at),
        "record_count": record_count,
        "indicator_count": indicator_count,
        "warnings": warnings,
        "details": {
            "workflow": os.getenv("GITHUB_WORKFLOW", "monitor-policia"),
            "run_id": os.getenv("GITHUB_RUN_ID"),
            "outcome": (outcome or "success").strip().lower(),
            "data_changed": bool(data_changed),
            "current_year": status_data.get("current_year"),
            "previous_year": status_data.get("previous_year"),
            "check_mode": "remote-metadata-first",
        },
    }
    if cutoff:
        payload["source_cutoff_date"] = cutoff.isoformat()
        payload["period_label"] = status_data.get("period_label") or f"Corte al {cutoff.isoformat()}"
    if workflow_ok:
        payload["last_success_at"] = _iso_datetime(checked_at)
    if workflow_ok and data_changed:
        payload["last_change_detected_at"] = _iso_datetime(checked_at)
    return payload


def _heartbeat_url(api_url: str) -> str:
    base = api_url.strip().rstrip("/")
    return base if base.endswith("/source-center/heartbeat") else f"{base}/source-center/heartbeat"


def _request_github_oidc_token(audience: str = "sisc-source-center") -> Optional[str]:
    request_url = os.getenv("ACTIONS_ID_TOKEN_REQUEST_URL", "").strip()
    request_token = os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "").strip()
    if not request_url or not request_token:
        return None
    separator = "&" if "?" in request_url else "?"
    request = Request(
        f"{request_url}{separator}{urlencode({'audience': audience})}",
        headers={"Authorization": f"Bearer {request_token}"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        return str(result.get("value")) if isinstance(result, dict) and result.get("value") else None
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        print(f"[AVISO] No se pudo obtener la identidad OIDC de GitHub: {error}.")
        return None


def send_heartbeat(
    payload: Dict[str, Any],
    *,
    api_url: Optional[str] = None,
    service_key: Optional[str] = None,
    oidc_token: Optional[str] = None,
    timeout: int = 60,
) -> bool:
    token = _request_github_oidc_token() if oidc_token is None else oidc_token.strip()
    key = (service_key if service_key is not None else os.getenv("SISC_SOURCE_MONITOR_KEY", "")).strip()
    if not token and not key:
        print("[AVISO] Heartbeat SISC omitido: no hay identidad OIDC ni clave de servicio.")
        return False

    headers = {"Content-Type": "application/json", "User-Agent": "monitor-policia/1.0"}
    headers["Authorization" if token else "X-SISC-SOURCE-KEY"] = f"Bearer {token}" if token else key
    request = Request(
        _heartbeat_url(api_url or os.getenv("SISC_API_URL", DEFAULT_API_URL)),
        data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                accepted = 200 <= response.status < 300
            print(f"[INFO] Heartbeat SISC enviado ({payload['status']}).")
            return accepted
        except HTTPError as error:
            print(f"[AVISO] El API SISC rechazo el heartbeat (HTTP {error.code}).")
            if error.code not in {408, 429, 500, 502, 503, 504}:
                return False
        except (URLError, TimeoutError, OSError):
            print(f"[AVISO] Fallo temporal de entrega SISC; intento {attempt + 1}/3.")
        if attempt < 2:
            time.sleep(2 ** (attempt + 1))
    return False


def main() -> int:
    changed = os.getenv("DATA_CHANGED", "false").strip().lower() == "true"
    payload = build_payload(
        outcome=os.getenv("SISC_MONITOR_OUTCOME", "success"),
        data_changed=changed,
    )
    Path("sisc-heartbeat.json").write_text(
        json.dumps(payload, ensure_ascii=True), encoding="utf-8"
    )
    print(
        "[INFO] Estado para Centro de fuentes: "
        f"{payload['status']} / {payload['quality_status']} / "
        f"{payload['indicator_count']} indicadores."
    )
    return 0 if send_heartbeat(payload) else 1


if __name__ == "__main__":
    raise SystemExit(main())
