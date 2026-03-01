from playwright.sync_api import sync_playwright
import json
from pathlib import Path

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"

urls_xlsx     = []   # URLs que terminan en .xlsx (descarga directa)
respuestas_doc = []  # Respuestas JSON con DocumentFile

def on_response(response):
    url = response.url
    # Capturar cualquier URL que termine en .xlsx
    if ".xlsx" in url.lower():
        urls_xlsx.append(url)
        return
    # Capturar JSONs con info de archivos
    if response.status != 200:
        return
    if "json" not in response.headers.get("content-type","").lower():
        return
    try:
        data = response.json()
        buscar_doc(data, url)
    except:
        pass

def buscar_doc(obj, src, nivel=0):
    if nivel > 7: return
    if isinstance(obj, dict):
        if obj.get("type") == "DocumentFile":
            fields = obj.get("fields", {})
            nombre = (fields.get("name") or obj.get("name") or "").strip()
            if nombre.upper().endswith(".XLSX"):
                # Guardar el objeto completo para inspeccionarlo
                respuestas_doc.append({
                    "nombre": nombre,
                    "id": obj.get("id",""),
                    "links": obj.get("links", []),
                    "src": src[:150]
                })
        for v in obj.values():
            if isinstance(v, (dict,list)): buscar_doc(v, src, nivel+1)
    elif isinstance(obj, list):
        for i in obj: buscar_doc(i, src, nivel+1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.on("response", on_response)
    try:
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    except: pass
    page.wait_for_timeout(8000)
    for i in range(6):
        page.evaluate(f"window.scrollTo(0, {i*600})")
        page.wait_for_timeout(700)

    # Intentar hacer clic en el primer archivo para ver qué URL genera
    print("Intentando clic en primer enlace .xlsx...")
    try:
        with page.expect_download(timeout=10000) as dl:
            page.click("a[href*='.xlsx'], a[href*='rendition']", timeout=5000)
        print(f"URL de descarga por clic: {dl.value.url}")
    except Exception as e:
        print(f"No se pudo hacer clic: {e}")

    browser.close()

print("\n" + "="*60)
print("URLs .xlsx capturadas en red:")
for u in urls_xlsx[:10]:
    print(f"  {u}")

print("\n" + "="*60)
print(f"DocumentFiles encontrados: {len(respuestas_doc)}")
if respuestas_doc:
    # Mostrar el primero completo
    doc = respuestas_doc[0]
    print(f"\nEjemplo - {doc['nombre']}:")
    print(f"  ID: {doc['id']}")
    print(f"  Links ({len(doc['links'])}):")
    for link in doc['links']:
        print(f"    rel={link.get('rel','')}  href={link.get('href','')[:120]}")
    print(f"  Fuente API: {doc['src']}")
