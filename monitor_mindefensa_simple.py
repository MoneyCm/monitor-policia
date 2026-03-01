from requests_html import HTMLSession
import re
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

print("="*80)
print("🔍 MONITOR MINDEFENSA - requests-html (JS ligero)")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
OUTPUT_CSV = Path("listado_mindefensa_simple.csv")

session = HTMLSession()

print("📡 Cargando página con renderizado JS...")
try:
    r = session.get(URL, timeout=45)
    print("✅ Página cargada")
    
    # Renderizar JavaScript (esto ejecuta el contenido dinámico)
    print("⏳ Renderizando JavaScript (puede tardar 10-20s)...")
    r.html.render(sleep=5, keep_page=True, scrolldown=2)
    
    html = r.html.html
    archivos = []
    
    # Buscar patrón: NOMBRE.xlsx + fecha
    patron = r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)\s*[\n\s]*([\d/]+,\s*[\d:]+)'
    matches = re.findall(patron, html, re.IGNORECASE)
    
    for nombre, fecha in matches:
        archivos.append({
            "nombre": nombre.strip(),
            "fecha": fecha.strip(),
            "url": f"https://www.mindefensa.gov.co/sites/default/files/datos-y-cifras/{nombre.replace(' ', '%20')}"
        })
    
    # Eliminar duplicados
    vistos = set()
    unicos = []
    for a in archivos:
        if a["nombre"].upper() not in vistos:
            vistos.add(a["nombre"].upper())
            unicos.append(a)
    
    if unicos:
        print(f"\n✅ Encontrados {len(unicos)} archivos:\n")
        for i, arch in enumerate(sorted(unicos, key=lambda x: x["nombre"]), 1):
            print(f"{i:2d}. {arch['nombre']:<50} {arch['fecha']}")
        
        # Guardar CSV
        df = pd.DataFrame(unicos)
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"\n💾 Guardado en: {OUTPUT_CSV}")
    else:
        print("\n⚠️ No se encontraron archivos .xlsx")
        print("💡 Probando búsqueda alternativa en enlaces...")
        
        # Buscar enlaces directos
        enlaces = r.html.find('a[href*=".xlsx"]')
        if enlaces:
            print(f"✅ Encontrados {len(enlaces)} enlaces .xlsx:")
            for i, link in enumerate(enlaces[:20], 1):
                texto = link.text or link.attrs.get('href', 'Sin texto')
                print(f"{i}. {texto[:60]}")
        else:
            print("❌ Tampoco encontró enlaces .xlsx")
            print("\n📄 Últimos 1500 caracteres del HTML renderizado:")
            print("-"*80)
            print(html[-1500:])
            
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
finally:
    session.close()

print("\n" + "="*80)
print("✅ Proceso completado")
