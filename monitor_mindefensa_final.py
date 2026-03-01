"""
MONITOR MINDEFENSA - VERSIÓN FINAL
"""
from playwright.sync_api import sync_playwright
import json, requests, pandas as pd, time
from datetime import datetime
from pathlib import Path

print("=" * 80)
print("🔍 MONITOR MINDEFENSA - FINAL")
print("=" * 80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 80 + "\n")

URL          = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE   = Path("mindefensa_state.json")
OUTPUT_CSV   = Path("mindefensa_archivos.csv")
DOWNLOAD_DIR = Path("mindefensa_xlsx")
DOWNLOAD_DIR.mkdir(exist_ok=True)

CHANNEL_TOKEN = "86fd5ad8af1b4db2b56bfc60a05ec867"
JAMUNDI_CODE  = 76364

ARCHIVOS_INTERES = {
    "HOMICIDIO INTENCIONAL", "SECUESTRO", "EXTORSION",
    "HURTO PERSONAS", "VIOLENCIA INTRAFAMILIAR",
    "DELITOS INFORMATICOS", "TERRORISMO", "MASACRES"
}

archivos_raw       = []
cookies_capturadas = []

def on_response(response):
    if response.status != 200:
        return
    if "json" not in response.headers.get("content-type", ""):
        return
    try:
        recorrer_json(response.json(), response.url)
    except Exception:
        pass

def recorrer_json(obj, src_url, nivel=0):
    if nivel > 7:
        return
    if isinstance(obj, dict):
        if obj.get("type") == "DocumentFile":
            fields = obj.get("fields", {})
            nombre = (fields.get("name") or fields.get("displayName") or obj.get("name") or "").strip()
            if nombre.upper().endswith(".XLSX"):
                item_id = obj.get("id", "")
                fecha   = fields.get("updatedDate") or obj.get("updatedDate", "")
                download_url = None
                for link in obj.get("links", []):
                    rel  = link.get("rel", "").lower()
                    href = link.get("href", "")
                    if href and ("rendition" in rel or "download" in rel or "rendition" in href.lower()):
                        if CHANNEL_TOKEN not in href:
                            sep = "&" if "?" in href else "?"
                            href += f"{sep}channelToken={CHANNEL_TOKEN}"
                        download_url = href
                        break
                if not download_url and item_id:
                    base = "https://www.mindefensa.gov.co/sites/web/content/published/api/v1.1"
                    download_url = f"{base}/{item_id}/renditions/Attachment?channelToken={CHANNEL_TOKEN}"
                archivos_raw.append({"nombre": nombre, "id": item_id, "fecha": fecha, "download_url": download_url or ""})
        for v in obj.values():
            if isinstance(v, (dict, list)):
                recorrer_json(v, src_url, nivel + 1)
    elif isinstance(obj, list):
        for item in obj:
            recorrer_json(item, src_url, nivel + 1)

def descargar(nombre, url, cookies_dict):
    if not url:
        return False, 0
    url_alt = url.replace("/renditions/Attachment", "/rendition") if "/renditions/Attachment" in url else url.replace("/rendition", "/renditions/Attachment")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Referer": URL,
        "Accept": "*/*",
    }
    for intento, u in enumerate([url, url_alt], 1):
        try:
            r = requests.get(u, headers=headers, cookies=cookies_dict, timeout=90, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 5000:
                dest = DOWNLOAD_DIR / nombre
                dest.write_bytes(r.content)
                return True, len(r.content)
            else:
                print(f"      intento {intento} HTTP {r.status_code} ({len(r.content)} bytes)")
        except Exception as e:
            print(f"      intento {intento} error: {e}")
        time.sleep(1)
    return False, 0

def analizar_jamundi(ruta):
    try:
        df = pd.read_excel(ruta, engine="openpyxl")
        df.columns = [str(c).lower().strip() for c in df.columns]
        col_muni = next((c for c in df.columns if any(x in c for x in ["cod_muni","municipio","mpio"])), None)
        if not col_muni:
            return {}
        mask = (df[col_muni].astype(str).str.strip() == str(JAMUNDI_CODE)) | (df[col_muni].astype(str).str.upper().str.contains("JAMUNDI", na=False))
        df_j = df[mask]
        res = {"jamundi": len(df_j), "total": len(df)}
        col_fecha = next((c for c in df.columns if any(x in c for x in ["anio","ano","year","fecha"])), None)
        if col_fecha and len(df_j):
            años = sorted(df_j[col_fecha].dropna().astype(str).str[:4].unique().tolist())
            res["años"] = años
        return res
    except Exception as e:
        return {"error": str(e)}

def main():
    print("📡 FASE 1: Detectando archivos...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page    = browser.new_page()
        page.on("response", on_response)
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"   aviso: {e}")
        page.wait_for_timeout(7000)
        for i in range(6):
            page.evaluate(f"window.scrollTo(0, {i * 600})")
            page.wait_for_timeout(700)
        for c in page.context.cookies():
            cookies_capturadas.append(c)
        browser.close()

    cookies_dict = {c["name"]: c["value"] for c in cookies_capturadas}
    vistos, unicos = set(), []
    for a in archivos_raw:
        clave = a["nombre"].upper().strip()
        if clave and clave not in vistos:
            vistos.add(clave)
            unicos.append(a)
    print(f"   ✅ {len(unicos)} archivos encontrados")

    print("\n🔍 FASE 2: Comparando con estado anterior...")
    estado = {}
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            estado = json.load(f)
    previos    = estado.get("archivos", {})
    nuevos     = [a for a in unicos if a["nombre"] not in previos]
    con_cambio = [a for a in unicos if a["nombre"] in previos and a["fecha"] != previos[a["nombre"]].get("fecha","")]
    print(f"   🆕 Nuevos: {len(nuevos)}  |  🔄 Actualizados: {len(con_cambio)}  |  ✅ Sin cambios: {len(unicos)-len(nuevos)-len(con_cambio)}")

    para_descargar = (nuevos + con_cambio)[:15]
    descargados = 0
    if para_descargar:
        print(f"\n📥 FASE 3: Descargando {len(para_descargar)} archivo(s)...")
        for arch in para_descargar:
            print(f"   → {arch['nombre']}")
            ok, size = descargar(arch["nombre"], arch["download_url"], cookies_dict)
            if ok:
                descargados += 1
                print(f"      ✅ {size//1024} KB")
            else:
                print(f"      ❌ No descargado")
        print(f"\n   Total: {descargados}/{len(para_descargar)}")
    else:
        print("\n✅ FASE 3: Sin cambios, nada que descargar")

    print("\n📊 FASE 4: Análisis Jamundí...")
    for xlsx in sorted(DOWNLOAD_DIR.glob("*.xlsx")):
        base = xlsx.stem.upper()
        # Comparar sin tildes (simple)
        import unicodedata
        base_norm = ''.join(c for c in unicodedata.normalize('NFD', base) if unicodedata.category(c) != 'Mn')
        if any(inter in base_norm for inter in ARCHIVOS_INTERES):
            res = analizar_jamundi(xlsx)
            if "jamundi" in res:
                detalle = f"  |  Años: {', '.join(res['años'])}" if "años" in res else ""
                print(f"   {xlsx.name}: {res['jamundi']:,} Jamundí / {res['total']:,} total{detalle}")
            elif "error" in res:
                print(f"   {xlsx.name}: ⚠️  {res['error']}")

    print("\n💾 FASE 5: Guardando estado...")
    estado["ultima_revision"] = datetime.now().isoformat()
    estado["archivos"] = {a["nombre"]: {"fecha": a["fecha"], "id": a["id"]} for a in unicos}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)

    csv_dest = OUTPUT_CSV
    try:
        if csv_dest.exists():
            csv_dest.unlink()
    except PermissionError:
        csv_dest = OUTPUT_CSV.with_stem(f"{OUTPUT_CSV.stem}_{datetime.now().strftime('%H%M%S')}")

    pd.DataFrame([{"nombre": a["nombre"], "fecha": a["fecha"], "download_url": a["download_url"]} for a in unicos]).to_csv(csv_dest, index=False, encoding="utf-8-sig")
    print(f"   ✅ CSV: {csv_dest}")
    print(f"   ✅ Estado: {STATE_FILE}")
    print("\n" + "="*80)
    print("✅ COMPLETADO")
    print("="*80)
    print(f"\nXLSX descargados en: {DOWNLOAD_DIR.resolve()}")

if __name__ == "__main__":
    main()
