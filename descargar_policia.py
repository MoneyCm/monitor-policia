"""
descargar_policia.py — Descarga dinámica de Excel de la Policía Nacional.
Recorre el selector de años para descubrir todos los XLSX publicados.
"""

import os
import sys
import time
import requests
import re
from pathlib import Path
from urllib.parse import urljoin, unquote
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import unicodedata
from playwright.sync_api import sync_playwright

CARPETA = "policia_xlsx"
URL_WEB  = "https://www.policia.gov.co/index.php/estadistica-delictiva-old"
BASE_URL = "https://www.policia.gov.co/sites/default/files/delitos-impacto/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.policia.gov.co/",
}

YEAR_RE = re.compile(r"\b20\d{2}\b")
XLSX_RE = re.compile(r"https?://[^\s\"'<>]+\.xlsx|/[^\"'<> ]+\.xlsx", re.I)

def _parse_list_env(name: str):
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def _pick_delitos(opts: list[dict], max_n: int) -> list[dict]:
    """
    Reduce una lista potencialmente enorme de 'delitos' a un subconjunto estable.
    Si encuentra coincidencias con delitos "core", prioriza esos; si no, toma los primeros max_n.
    """
    if len(opts) <= max_n:
        return opts

    core = [
        "abigeato",
        "amenazas",
        "delitos sexuales",
        "extorsion",
        "homicidios",
        "homicidio intencional",
        "homicidios en accidente de transito",
        "hurto a personas",
        "hurto a residencias",
        "hurto de automotores",
        "hurto de motocicletas",
        "hurto a comercio",
        "hurto a entidades comerciales",
        "hurto a entidades financieras",
        "lesiones personales",
        "lesiones en accidente de transito",
        "violencia intrafamiliar",
        "secuestro",
        "terrorismo",
        "pirateria terrestre",
    ]
    core_n = {_norm(x) for x in core}

    picked = []
    seen = set()
    for o in opts:
        lab = _norm(o.get("label") or "")
        if not lab or lab in seen:
            continue
        if any(c in lab for c in core_n):
            picked.append(o)
            seen.add(lab)

    if picked:
        return picked[:max_n]

    return opts[:max_n]

def calcular_fingerprint(urls: list[str]) -> str:
    """
    Calcula un fingerprint remoto rapido sin descargar contenidos.
    Usa cabeceras HTTP (ETag/Last-Modified/Content-Length) y la URL.
    """
    urls_unique = sorted(set(urls))
    rows: list[str] = [""] * len(urls_unique)

    # En GitHub Actions, hacer 36-40 HEAD secuenciales puede tardar >10 min si el servidor tarda en responder.
    # Esto paraleliza la consulta de metadatos y reduce el timeout para evitar acumulacion.
    timeout_total = float(os.environ.get("POLICIA_FP_TIMEOUT", "12"))
    timeout = (5.0, timeout_total)  # (connect, read)
    workers = int(os.environ.get("POLICIA_FP_WORKERS", "8"))

    def fetch_meta(i: int, url: str) -> tuple[int, str]:
        etag = ""
        last_modified = ""
        length = ""
        try:
            r = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code == 405:
                r.close()
                r = requests.get(url, headers=HEADERS, timeout=timeout, stream=True, allow_redirects=True)
            etag = (r.headers.get("ETag") or "").strip()
            last_modified = (r.headers.get("Last-Modified") or "").strip()
            length = (r.headers.get("Content-Length") or "").strip()
            try:
                r.close()
            except Exception:
                pass
        except Exception:
            # Si falla, dejamos cabeceras vacias pero aun incluimos URL para estabilidad.
            pass
        return i, f"{url}\t{etag}\t{last_modified}\t{length}"

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(fetch_meta, i, url) for i, url in enumerate(urls_unique)]
        for fut in as_completed(futs):
            i, row = fut.result()
            rows[i] = row

    payload = "\n".join(rows).encode("utf-8", errors="replace")
    return hashlib.md5(payload).hexdigest()

def obtener_enlaces_actuales():
    """Busca enlaces XLSX recorriendo las opciones del menú de años."""
    print(f"Buscando enlaces en: {URL_WEB}")
    enlaces = {}

    def registrar_enlaces(page, origen):
        def agregar(url_raw):
            if not url_raw:
                return
            full_url = urljoin(URL_WEB, url_raw)
            if ".xlsx" in full_url.lower() and "delitos-impacto" in full_url:
                enlaces[full_url] = origen

        for a in page.query_selector_all("a[href]"):
            href = a.get_attribute("href") or ""
            agregar(href)

        # Algunos resultados llegan en onclick/data-* y no en href visible.
        for el in page.query_selector_all("[onclick], [data-url], [data-href]"):
            onclick = el.get_attribute("onclick") or ""
            data_url = el.get_attribute("data-url") or ""
            data_href = el.get_attribute("data-href") or ""
            for candidate in (data_url, data_href, onclick):
                for match in XLSX_RE.findall(candidate):
                    agregar(match)

        # Respaldo: buscar rutas xlsx en el HTML renderizado.
        try:
            html = page.content()
            for match in XLSX_RE.findall(html):
                agregar(match)
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            page.on("response", lambda resp: (
                enlaces.__setitem__(resp.url, "network_response")
                if (".xlsx" in resp.url.lower() and "delitos-impacto" in resp.url.lower())
                else None
            ))
            resp = page.goto(URL_WEB, wait_until="domcontentloaded", timeout=60000)
            try:
                status = resp.status if resp is not None else None
            except Exception:
                status = None
            if status and int(status) >= 400:
                registrar_enlaces(page, f"http_{status}")
                browser.close()
                raise RuntimeError(f"HTTP {status} al cargar la pagina.")
            page.wait_for_timeout(3000)

            # Detectar selects: delito vs año
            selects = page.query_selector_all("select")
            if len(selects) < 2:
                registrar_enlaces(page, "vista_inicial")
                browser.close()
                raise RuntimeError("No se detectaron selects de filtro (delito/año).")

            def opciones_de(select):
                opts = []
                for o in select.query_selector_all("option"):
                    v = (o.get_attribute("value") or "").strip()
                    t = (o.inner_text() or "").strip()
                    opts.append({"value": v, "label": t})
                return opts

            scored = []
            for idx, s in enumerate(selects):
                opts = opciones_de(s)
                year_like = sum(1 for o in opts if YEAR_RE.fullmatch(o["label"]) or YEAR_RE.fullmatch(o["value"]))
                scored.append((year_like, len(opts), idx, opts))

            # El select "año" tiene muchas opciones tipo 20xx
            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
            year_like, _, idx_anio, opts_anio = scored[0]
            if year_like < 5:
                registrar_enlaces(page, "vista_inicial")
                browser.close()
                raise RuntimeError("No se pudo identificar el select de años.")

            # El otro select lo tomamos como "delito"
            idx_delito = next((i for i in range(len(selects)) if i != idx_anio), None)
            select_delito = selects[idx_delito] if idx_delito is not None else None
            opts_delito = opciones_de(select_delito) if select_delito else []

            # Preparar listas (permiten override por variables de entorno)
            years_allow = _parse_list_env("POLICIA_YEARS")  # ej: "2024,2025"
            delitos_allow = _parse_list_env("POLICIA_DELITOS")  # ej: "Amenazas,Extorsión"

            years = []
            for o in opts_anio:
                lab = o["label"]
                if not YEAR_RE.fullmatch(lab):
                    continue
                if years_allow and lab not in years_allow:
                    continue
                years.append(o)

            # Por defecto, usar solo los 2 años más recientes del menú.
            if not years_allow:
                years = sorted(years, key=lambda x: int(x["label"]))[-2:]
                if os.environ.get("POLICIA_FP_MODE") == "1":
                    # Para fingerprint, con 1 año suele ser suficiente y reduce tiempo.
                    years = years[-1:]

            delitos = []
            for o in opts_delito:
                lab = (o["label"] or "").strip()
                if not lab or "any" in lab.lower():
                    continue
                if delitos_allow and lab not in delitos_allow:
                    continue
                delitos.append(o)

            if os.environ.get("POLICIA_FP_MODE") == "1" and not delitos_allow:
                max_delitos = int(os.environ.get("POLICIA_FP_DELITOS_MAX", "12"))
                delitos = delitos[:max(1, max_delitos)]

            # Modo general: si la pagina expone demasiados delitos, recortar a un subconjunto estable
            # para evitar cientos de combinaciones y timeouts en GitHub Actions.
            if not delitos_allow:
                max_delitos_general = int(os.environ.get("POLICIA_DELITOS_MAX", "40"))
                delitos = _pick_delitos(delitos, max_delitos_general)

            print(f"Selector de años: {len(years)} opciones; selector de delitos: {len(delitos)} opciones")

            btn_buscar = page.locator("button:has-text('Buscar')").first
            if btn_buscar.count() == 0:
                registrar_enlaces(page, "vista_inicial")
                browser.close()
                raise RuntimeError("No se encontró botón 'Buscar'.")

            # Recorrer combinaciones: año + delito + Buscar
            for y in years:
                try:
                    # Reubicar selects en cada iteración (el DOM cambia tras buscar)
                    select_anio_live = page.locator("select").nth(idx_anio)
                    if y["value"]:
                        select_anio_live.select_option(value=y["value"])
                    else:
                        select_anio_live.select_option(label=y["label"])
                except Exception:
                    continue

                for d in delitos:
                    try:
                        select_delito_live = page.locator("select").nth(idx_delito)
                        if d["value"]:
                            select_delito_live.select_option(value=d["value"])
                        else:
                            select_delito_live.select_option(label=d["label"])

                        btn_buscar.click()
                        page.wait_for_timeout(1500)
                        page.wait_for_load_state("domcontentloaded", timeout=15000)

                        registrar_enlaces(page, f"{y['label']}|{d['label']}")
                    except Exception:
                        continue

            browser.close()

        if enlaces:
            print(f"Encontrados {len(enlaces)} enlaces únicos desde el menú")
            return list(enlaces.keys())

        # Respaldo por HTML inicial si el menú no expone enlaces al navegador
        r = requests.get(URL_WEB, headers=HEADERS, timeout=30)
        r.raise_for_status()
        html = r.text
        for href in re.findall(r'href=["\']([^"\']+\.xlsx)["\']', html, re.I):
            full_url = urljoin(URL_WEB, href)
            if "delitos-impacto" in full_url:
                enlaces[full_url] = "html_inicial"

        print(f"Encontrados {len(enlaces)} enlaces únicos por HTML")
        return list(enlaces.keys())
    except Exception as e:
        print(f"Error al obtener enlaces: {e}")
        return []

def descargar(url: str, destino: Path, reintentos: int = 2) -> bool:
    """Descarga un archivo. Retorna True si exitoso."""
    for intento in range(1, reintentos + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
            if r.status_code == 404:
                return False
            r.raise_for_status()
            with open(destino, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception:
            time.sleep(2 * intento)
    return False

def main():
    if "--fingerprint" in sys.argv:
        enlaces = obtener_enlaces_actuales()
        if not enlaces:
            print("ERROR: No se pudieron descubrir enlaces XLSX (posible bloqueo/403).", file=sys.stderr)
            sys.exit(2)
        fp = calcular_fingerprint(enlaces)
        # Salida pensada para GitHub Actions: un solo valor en stdout.
        print(fp)
        return

    carpeta = Path(CARPETA)
    carpeta.mkdir(exist_ok=True)

    enlaces = obtener_enlaces_actuales()
    
    if not enlaces:
        print("No se detectaron enlaces dinámicos.")
        return

    ok = 0
    fallo = 0

    print("=" * 60)
    print("DESCARGA DINÁMICA POLICÍA NACIONAL")
    print("=" * 60)

    for url in sorted(enlaces):
        nombre_archivo = os.path.basename(url)
        nombre_local = unquote(nombre_archivo)
        destino = carpeta / nombre_local
        
        # ASCII only para consolas Windows (evita UnicodeEncodeError con cp1252)
        print(f"-> Procesando: {nombre_local}")
        
        # Cache: Si ya existe y pesa más de 5KB, no descargar
        if destino.exists() and destino.stat().st_size > 5000:
            print(f"    [CACHE] Ya existe.")
            ok += 1
            continue
            
        if descargar(url, destino):
            print(f"    [OK] Descargado ({destino.stat().st_size // 1024} KB)")
            ok += 1
        else:
            print(f"    [FALLO] No se pudo descargar.")
            fallo += 1
        
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"Descargados/Cache: {ok}  |  Fallidos: {fallo}")
    print("=" * 60)

if __name__ == "__main__":
    main()
