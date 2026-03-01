from playwright.sync_api import sync_playwright
import json
import re
import pandas as pd
from datetime import datetime
from pathlib import Path

print("="*80)
print("🔍 MONITOR MINDEFENSA - INTERCEPTANDO APIS")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
OUTPUT_CSV = Path("listado_mindefensa_api.csv")

archivos_encontrados = []
apis_capturadas = []

def interceptar_respuesta(response):
    """Captura respuestas de red que puedan contener datos de archivos"""
    url = response.url
    status = response.status
    
    # Filtrar solo respuestas exitosas con JSON
    if status == 200 and "json" in response.headers.get("content-type", "").lower():
        try:
            data = response.json()
            apis_capturadas.append({"url": url, "data_preview": str(data)[:200]})
            
            # Buscar archivos .xlsx en la respuesta JSON
            buscar_en_json(data, url)
        except:
            pass

def buscar_en_json(obj, origen, nivel=0):
    """Busca recursivamente nombres de archivos .xlsx en estructuras JSON"""
    if nivel > 5:  # Evitar recursión infinita
        return
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            # Buscar campos que parezcan nombres de archivo
            if isinstance(key, str) and ".xlsx" in key.upper():
                archivos_encontrados.append({"nombre": key, "fuente": origen, "fecha": "N/A"})
            if isinstance(value, str) and value.upper().endswith(".XLSX"):
                archivos_encontrados.append({"nombre": value, "fuente": origen, "fecha": "N/A"})
            # Buscar en valores anidados
            if isinstance(value, (dict, list)):
                buscar_en_json(value, origen, nivel+1)
    
    elif isinstance(obj, list):
        for item in obj:
            buscar_en_json(item, origen, nivel+1)
    
    elif isinstance(obj, str) and ".xlsx" in obj.upper():
        # Extraer nombre limpio
        match = re.search(r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)', obj, re.IGNORECASE)
        if match:
            archivos_encontrados.append({"nombre": match.group(1).strip(), "fuente": origen, "fecha": "N/A"})

with sync_playwright() as p:
    print("🚀 Lanzando Chromium con interceptación de red...")
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    page = context.new_page()
    
    # Activar interceptación de respuestas
    page.on("response", interceptar_respuesta)
    
    try:
        print(f"📡 Navegando a: {URL}")
        page.goto(URL, wait_until='networkidle', timeout=60000)
        
        # Esperar y hacer scroll para trigger de lazy-loading
        print("⏳ Esperando carga dinámica y haciendo scroll...")
        page.wait_for_timeout(3000)
        for i in range(5):
            page.evaluate(f"window.scrollTo(0, {i*500})")
            page.wait_for_timeout(500)
        
        # Esperar respuestas de red adicionales
        page.wait_for_timeout(2000)
        
        # También buscar en el DOM renderizado por si acaso
        print("🔍 Buscando en el DOM renderizado...")
        elementos = page.query_selector_all('a[href*=".xlsx"], span:has-text(".xlsx"), div:has-text(".xlsx")')
        for el in elementos[:50]:  # Limitar para no saturar
            texto = el.text_content().strip()
            if '.xlsx' in texto.upper():
                match = re.search(r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)', texto, re.IGNORECASE)
                if match and match.group(1) not in [a["nombre"] for a in archivos_encontrados]:
                    archivos_encontrados.append({"nombre": match.group(1).strip(), "fuente": "DOM", "fecha": "N/A"})
        
        # Eliminar duplicados
        vistos = set()
        unicos = []
        for a in archivos_encontrados:
            clave = a["nombre"].upper().strip()
            if clave and clave not in vistos:
                vistos.add(clave)
                unicos.append(a)
        
        # Si aún no hay resultados, mostrar diagnóstico
        if not unicos:
            print("\n⚠️ No se encontraron archivos .xlsx en APIs ni DOM")
            print(f"\n📡 APIs JSON capturadas ({len(apis_capturadas)}):")
            for api in apis_capturadas[:5]:
                print(f"   • {api['url'][:80]}...")
                print(f"     Preview: {api['data_preview'][:150]}...")
            
            print(f"\n📄 Últimos 2000 chars del HTML:")
            print("-"*80)
            print(page.content()[-2000:])
        else:
            print(f"\n✅ Encontrados {len(unicos)} archivos:\n")
            for i, arch in enumerate(sorted(unicos, key=lambda x: x["nombre"]), 1):
                print(f"{i:2d}. {arch['nombre']:<50} [{arch['fuente']}]")
            
            # Guardar CSV
            df = pd.DataFrame(unicos)
            df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
            print(f"\n💾 Guardado en: {OUTPUT_CSV}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        browser.close()
        print("\n🔚 Navegador cerrado")

print("\n" + "="*80)
print("✅ Proceso completado")
