"""
descargar_policia.py — Descarga dinámica de Excel de la Policía Nacional
Extrae los enlaces directamente de la web de la policía para evitar nombres hardcoded.
"""

import os
import time
import requests
import re
from pathlib import Path
from urllib.parse import urljoin, quote

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

def obtener_enlaces_actuales():
    """Busca en la página de la policía todos los enlaces a archivos XLSX."""
    print(f"🔍 Buscando enlaces en: {URL_WEB}")
    try:
        r = requests.get(URL_WEB, headers=HEADERS, timeout=30)
        r.raise_for_status()
        html = r.text
        
        # Buscar enlaces que terminen en .xlsx (pueden estar en href o src)
        enlaces = re.findall(r'href=["\']([^"\']+\.xlsx)["\']', html, re.I)
        
        enlaces_completos = []
        for e in enlaces:
            full_url = urljoin(URL_WEB, e)
            if "delitos-impacto" in full_url:
                enlaces_completos.append(full_url)
        
        print(f"✅ Encontrados {len(enlaces_completos)} enlaces de delitos en la página.")
        return list(set(enlaces_completos))
    except Exception as e:
        print(f"❌ Error al obtener enlaces: {e}")
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
    carpeta = Path(CARPETA)
    carpeta.mkdir(exist_ok=True)

    enlaces = obtener_enlaces_actuales()
    
    if not enlaces:
        print("⚠️ No se detectaron enlaces dinámicos. Usando respaldo interno...")
        # Aquí podrías poner una lista de respaldo si quisieras, 
        # pero el objetivo es que sea dinámico.
        return

    ok = 0
    fallo = 0

    print("=" * 60)
    print("DESCARGA DINÁMICA POLICÍA NACIONAL")
    print("=" * 60)

    # Filtrar solo años de interés: 2024 y 2025
    enlaces_filtrados = [e for e in enlaces if "2024" in e or "2025" in e]
    
    for url in sorted(enlaces_filtrados):
        nombre_archivo = os.path.basename(url)
        # Limpiar el nombre de caracteres codificados para el archivo local
        nombre_local = nombre_archivo.replace("%20", " ")
        destino = carpeta / nombre_local
        
        print(f"→ Procesando: {nombre_local}")
        
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
    print(f"✅ Descargados/Cache: {ok}  |  ❌ Fallidos: {fallo}")
    print("=" * 60)

if __name__ == "__main__":
    main()
