from playwright.sync_api import sync_playwright
import json, re, pandas as pd, hashlib
from datetime import datetime
from pathlib import Path

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE = Path("mindefensa_monitor_state.json")
OUTPUT_CSV = Path("listado_mindefensa_con_fecha.csv")

def extraer_archivos(page):
    archivos = []
    # Buscar en el DOM renderizado
    elementos = page.query_selector_all('[href*=".xlsx"], text:has-text(".xlsx")')
    for el in elementos:
        texto = el.text_content().strip() if hasattr(el, 'text_content') else str(el)
        if '.xlsx' in texto.upper():
            match = re.search(r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)', texto, re.IGNORECASE)
            if match:
                # Intentar extraer fecha del contexto cercano
                fecha = "N/A"
                fecha_match = re.search(r'([\d/]+,\s*[\d:]+)', texto)
                if fecha_match:
                    fecha = fecha_match.group(1).strip()
                archivos.append({"nombre": match.group(1).strip(), "fecha_pagina": fecha})
    return archivos

def cargar_estado():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"archivos": {}}

def main():
    print("🔍 MONITOR MINDEFENSA - CON SEGUIMIENTO DE FECHAS")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        page.goto(URL, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)
        
        archivos_actuales = extraer_archivos(page)
        browser.close()
    
    # Eliminar duplicados
    vistos = set()
    unicos = []
    for a in archivos_actuales:
        if a["nombre"].upper() not in vistos:
            vistos.add(a["nombre"].upper())
            unicos.append(a)
    
    # Comparar con estado anterior
    estado = cargar_estado()
    previos = estado.get("archivos", {})
    
    cambios = []
    for arch in unicos:
        nombre = arch["nombre"]
        if nombre not in previos:
            cambios.append({"tipo": "🆕 NUEVO", "archivo": nombre, "fecha_nueva": arch["fecha_pagina"]})
        elif previos[nombre].get("fecha_pagina") != arch["fecha_pagina"]:
            cambios.append({"tipo": "🔄 ACTUALIZADO", "archivo": nombre, 
                          "fecha_anterior": previos[nombre].get("fecha_pagina"),
                          "fecha_nueva": arch["fecha_pagina"]})
    
    # Mostrar resultados
    print(f"\n📊 Total archivos: {len(unicos)}")
    if cambios:
        print(f"\n⚠️ CAMBIOS DETECTADOS ({len(cambios)}):")
        for c in cambios:
            if c["tipo"] == "🆕 NUEVO":
                print(f"   {c['tipo']}: {c['archivo']} (fecha: {c['fecha_nueva']})")
            else:
                print(f"   {c['tipo']}: {c['archivo']} ({c['fecha_anterior']} → {c['fecha_nueva']})")
    else:
        print("\n✅ Sin cambios desde la última revisión")
    
    # Guardar estado y CSV
    estado["ultima_revision"] = datetime.now().isoformat()
    estado["archivos"] = {a["nombre"]: a for a in unicos}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    
    df = pd.DataFrame(unicos)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n💾 Guardado en: {OUTPUT_CSV}")
    print(f"💾 Estado guardado en: {STATE_FILE}")

if __name__ == "__main__":
    main()
