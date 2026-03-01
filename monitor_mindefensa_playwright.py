from playwright.sync_api import sync_playwright
import re
import pandas as pd
from datetime import datetime
from pathlib import Path

print("="*80)
print("🔍 MONITOR MINDEFENSA - PLAYWRIGHT")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
OUTPUT_CSV = Path("listado_mindefensa_playwright.csv")

def extraer_archivos(page):
    """Extrae archivos después de que JavaScript cargue el contenido"""
    archivos = []
    
    # Esperar a que haya enlaces con .xlsx o texto que los contenga
    page.wait_for_timeout(5000)  # Esperar 5 segundos para carga dinámica
    
    # Obtener todo el texto visible de la página
    contenido = page.content()
    
    # Buscar patrón: NOMBRE.xlsx seguido de fecha
    patron = r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)\s*[\n\s]*([\d/]+,\s*[\d:]+)'
    matches = re.findall(patron, contenido, re.IGNORECASE)
    
    for nombre, fecha in matches:
        archivos.append({
            "nombre": nombre.strip(),
            "fecha": fecha.strip(),
            "url": f"https://www.mindefensa.gov.co/sites/default/files/datos-y-cifras/{nombre.replace(' ', '%20')}"
        })
    
    # También buscar enlaces directos por si acaso
    enlaces = page.query_selector_all('a[href*=".xlsx"]')
    for enlace in enlaces:
        texto = enlace.text_content().strip()
        href = enlace.get_attribute('href')
        if texto and '.xlsx' in texto and texto not in [a["nombre"] for a in archivos]:
            archivos.append({"nombre": texto, "fecha": "N/A", "url": href})
    
    # Eliminar duplicados
    vistos = set()
    unicos = []
    for a in archivos:
        clave = a["nombre"].upper().strip()
        if clave and clave not in vistos:
            vistos.add(clave)
            unicos.append(a)
    
    return unicos

with sync_playwright() as p:
    print("🚀 Lanzando Chromium con Playwright...")
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    page = context.new_page()
    
    try:
        print(f"📡 Cargando: {URL}")
        page.goto(URL, wait_until='networkidle', timeout=45000)
        
        print("⏳ Esperando contenido dinámico...")
        archivos = extraer_archivos(page)
        
        if archivos:
            print(f"\n✅ Encontrados {len(archivos)} archivos:\n")
            for i, arch in enumerate(sorted(archivos, key=lambda x: x["nombre"]), 1):
                print(f"{i:2d}. {arch['nombre']:<50} {arch['fecha']}")
            
            # Guardar CSV
            df = pd.DataFrame(archivos)
            df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
            print(f"\n💾 Guardado en: {OUTPUT_CSV}")
        else:
            print("\n⚠️ No se encontraron archivos .xlsx")
            print("💡 Contenido parcial de la página:")
            print(page.content()[:2000])
            
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    finally:
        browser.close()
        print("\n🔚 Navegador cerrado")

print("\n" + "="*80)
print("✅ Proceso completado")
