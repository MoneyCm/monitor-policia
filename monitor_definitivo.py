from playwright.sync_api import sync_playwright
import json, re, pandas as pd, hashlib
from datetime import datetime
from pathlib import Path

print("="*80)
print("🔍 MONITOR MINDEFENSA - DEFINITIVO CON SEGUIMIENTO")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE = Path("mindefensa_monitor_final.json")
OUTPUT_CSV = Path("listado_mindefensa_final.csv")

archivos_encontrados = []

def interceptar_respuesta(response):
    """Captura respuestas JSON de la API de Oracle SCS"""
    if response.status != 200:
        return
    content_type = response.headers.get("content-type", "").lower()
    if "json" not in content_type:
        return
    
    try:
        data = response.json()
        buscar_en_json(data)
    except:
        pass

def buscar_en_json(obj, nivel=0):
    """Busca recursivamente nombres de archivos .xlsx en JSON"""
    if nivel > 5:
        return
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.upper().endswith(".XLSX"):
                archivos_encontrados.append({"nombre": key.strip(), "fuente": "API"})
            if isinstance(value, str) and value.upper().endswith(".XLSX"):
                # Intentar extraer fecha del contexto si está disponible
                fecha = "N/A"
                archivos_encontrados.append({"nombre": value.strip(), "fecha_pagina": fecha, "fuente": "API"})
            if isinstance(value, (dict, list)):
                buscar_en_json(value, nivel+1)
    elif isinstance(obj, list):
        for item in obj:
            buscar_en_json(item, nivel+1)

def cargar_estado():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"archivos": {}}

def main():
    print("🚀 Iniciando monitoreo con Playwright + API interception...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        
        # Activar interceptación de respuestas
        page.on("response", interceptar_respuesta)
        
        print(f"📡 Navegando a: {URL}")
        page.goto(URL, wait_until='networkidle', timeout=60000)
        
        # Esperar y hacer scroll para trigger de lazy-loading
        print("⏳ Esperando carga dinámica...")
        page.wait_for_timeout(5000)
        for i in range(3):
            page.evaluate(f"window.scrollTo(0, {i*400})")
            page.wait_for_timeout(500)
        
        browser.close()
    
    # Eliminar duplicados
    vistos = set()
    unicos = []
    for a in archivos_encontrados:
        clave = a["nombre"].upper().strip()
        if clave and clave not in vistos:
            vistos.add(clave)
            # Intentar asignar fecha desde el estado anterior si existe
            unicos.append(a)
    
    print(f"\n✅ Encontrados {len(unicos)} archivos")
    
    # Comparar con estado anterior para detectar cambios
    estado = cargar_estado()
    previos = estado.get("archivos", {})
    
    cambios = []
    for arch in unicos:
        nombre = arch["nombre"]
        if nombre not in previos:
            cambios.append({"tipo": "🆕 NUEVO", "archivo": nombre})
        # Nota: Como no extraemos fecha dinámica, comparamos por presencia
    
    # Mostrar resultados
    print("\n📋 LISTADO DE ARCHIVOS:")
    print("-"*80)
    for i, arch in enumerate(sorted(unicos, key=lambda x: x["nombre"]), 1):
        icono = "🆕" if any(c["archivo"]==arch["nombre"] for c in cambios) else "  "
        print(f"{icono} {i:2d}. {arch['nombre']}")
    
    if cambios:
        print(f"\n⚠️ CAMBIOS DETECTADOS ({len(cambios)}):")
        for c in cambios:
            print(f"   • {c['tipo']}: {c['archivo']}")
    elif previos:
        print(f"\n✅ Sin cambios desde la última revisión ({estado.get('ultima_revision', 'desconocida')})")
    else:
        print(f"\nℹ️ Primera ejecución - estado inicial guardado")
    
    # Guardar estado y CSV
    estado["ultima_revision"] = datetime.now().isoformat()
    estado["archivos"] = {a["nombre"]: {"fecha_detectada": datetime.now().isoformat()} for a in unicos}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    
    df = pd.DataFrame(unicos)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    print(f"\n💾 Listado guardado en: {OUTPUT_CSV}")
    print(f"💾 Estado guardado en: {STATE_FILE}")
    print("\n🎯 Para ver cambios en el futuro: ejecutá este script nuevamente")

if __name__ == "__main__":
    main()
