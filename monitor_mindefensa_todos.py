import requests
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
import pandas as pd

print("🔍 MONITOR MINDEFENSA - TODOS LOS ARCHIVOS")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("Fuente: https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica")
print("="*80 + "\n")

# Configuración
URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE = Path("mindefensa_todos_archivos.json")
OUTPUT_CSV = Path("listado_completo_mindefensa.csv")

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def extraer_archivos(html):
    """Extrae TODOS los archivos con el patrón: NOMBRE.xlsx + fecha + fwadmin"""
    archivos = []
    categorias = []
    categoria_actual = "Sin categoría"
    
    # Primero extraer categorías (títulos antes de los archivos)
    lineas = html.split('\n')
    for i, linea in enumerate(lineas):
        # Detectar títulos de categoría (texto que no es archivo)
        if re.search(r'(Delitos|Avances|Resultados|Afectación|Desmovilización)', linea, re.IGNORECASE):
            if 'xlsx' not in linea and '.xls' not in linea:
                categoria_actual = linea.strip()
                if categoria_actual and categoria_actual not in categorias:
                    categorias.append(categoria_actual)
        
        # Detectar archivos
        match = re.search(r'([A-ZÁ-Ú\s]+\.xlsx)\s*\n*\s*([\d/]+,\s*[\d:]+)\s*\n*\s*(\w+)', linea, re.IGNORECASE)
        if match:
            nombre, fecha, usuario = match.groups()
            
            # URL de descarga
            url_base = "https://www.mindefensa.gov.co/sites/default/files/datos-y-cifras/"
            url_descarga = f"{url_base}{nombre.replace(' ', '%20')}"
            
            # Hash único
            hash_id = hashlib.md5(f"{nombre}{fecha}".encode()).hexdigest()[:10]
            
            archivos.append({
                "categoria": categoria_actual,
                "nombre": nombre.strip(),
                "fecha": fecha.strip(),
                "usuario": usuario.strip(),
                "url": url_descarga,
                "hash": hash_id
            })
    
    # Si no funcionó el patrón, intentar extracción más simple
    if len(archivos) == 0:
        print("🔍 Intentando extracción alternativa...")
        for match in re.finditer(r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)', html):
            nombre = match.group(1).strip()
            archivos.append({
                "categoria": "Sin categoría",
                "nombre": nombre,
                "fecha": "N/A",
                "usuario": "N/A",
                "url": f"https://www.mindefensa.gov.co/sites/default/files/datos-y-cifras/{nombre.replace(' ', '%20')}",
                "hash": hashlib.md5(nombre.encode()).hexdigest()[:10]
            })
    
    return archivos, categorias

def cargar_estado():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"revisiones": [], "archivos": {}}

def guardar_estado(estado):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)

def main():
    print("📡 Consultando MinDefensa...")
    
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return
    
    archivos_actuales, categorias = extraer_archivos(html)
    
    if not archivos_actuales:
        print("⚠️ No se encontraron archivos con el patrón esperado")
        print("💡 Posible causa: la página cambió su estructura HTML")
        print("\n📄 Fragmento del HTML para diagnóstico:")
        print(html[2000:4000])
        return
    
    print(f"✅ Encontrados {len(archivos_actuales)} archivos")
    print(f"📂 Categorías detectadas: {len(categorias)}\n")
    
    # Cargar estado previo
    estado = cargar_estado()
    previos = estado.get("archivos", {})
    
    # Detectar cambios
    nuevos = []
    actualizados = []
    sin_cambios = []
    
    for arch in archivos_actuales:
        nombre = arch["nombre"]
        if nombre not in previos:
            nuevos.append(arch)
        elif previos[nombre].get("hash") != arch["hash"]:
            actualizados.append({
                "nombre": nombre,
                "categoria": arch["categoria"],
                "fecha_anterior": previos[nombre].get("fecha"),
                "fecha_nueva": arch["fecha"]
            })
        else:
            sin_cambios.append(arch)
    
    # Mostrar resultados por categoría
    print("="*80)
    print("📊 RESULTADOS COMPLETOS")
    print("="*80)
    
    # Resumen general
    print(f"\n📋 RESUMEN:")
    print(f"   • Total archivos en página: {len(archivos_actuales)}")
    print(f"   • Nuevos desde última revisión: {len(nuevos)}")
    print(f"   • Actualizados desde última revisión: {len(actualizados)}")
    print(f"   • Sin cambios: {len(sin_cambios)}")
    print(f"   • Última revisión anterior: {estado.get('ultima_revision', 'N/A')}")
    
    # Listado completo por categoría
    print(f"\n📂 LISTADO COMPLETO POR CATEGORÍA:")
    print("-"*80)
    
    categorias_unicas = list(set(arch["categoria"] for arch in archivos_actuales))
    
    for cat in sorted(categorias_unicas):
        archivos_cat = [a for a in archivos_actuales if a["categoria"] == cat]
        print(f"\n{cat}")
        print("-"*60)
        for i, arch in enumerate(archivos_cat, 1):
            estado_icon = "🆕" if arch in nuevos else "🔄" if any(a["nombre"]==arch["nombre"] for a in actualizados) else "  "
            print(f"   {estado_icon} {i:2d}. {arch['nombre']:<45} {arch['fecha']:>20}")
    
    # Guardar CSV completo
    df = pd.DataFrame(archivos_actuales)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n💾 Listado completo guardado en: {OUTPUT_CSV}")
    
    # Guardar estado JSON
    estado["ultima_revision"] = datetime.now().isoformat()
    estado["archivos"] = {a["nombre"]: a for a in archivos_actuales}
    estado["historial"] = estado.get("historial", [])[-100:]
    if nuevos or actualizados:
        estado["historial"].append({
            "fecha": datetime.now().isoformat(),
            "nuevos": len(nuevos),
            "actualizados": len(actualizados),
            "total": len(archivos_actuales)
        })
    guardar_estado(estado)
    print(f"💾 Estado guardado en: {STATE_FILE}")
    
    # Alertas si hay cambios
    if nuevos or actualizados:
        print(f"\n🎯 ACCIÓN RECOMENDADA:")
        print(f"   1. Descargá los {len(nuevos)} archivos nuevos y {len(actualizados)} actualizados")
        print(f"   2. Ejecutá tu análisis de Jamundí con los nuevos datos")
        print(f"   3. Actualizá el informe para el Concejo")
        
        # Guardar log de cambios
        with open("cambios_mindefensa.log", "a", encoding="utf-8") as log:
            log.write(f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M')}] CAMBIOS DETECTADOS:\n")
            for a in nuevos:
                log.write(f"  🆕 [{a['categoria']}] {a['nombre']} | {a['fecha']}\n")
            for a in actualizados:
                log.write(f"  🔄 [{a['categoria']}] {a['nombre']} | {a['fecha_anterior']} → {a['fecha_nueva']}\n")
        print(f"📝 Alertas guardadas en: cambios_mindefensa.log")
    else:
        print(f"\n✅ Sin cambios desde la última revisión")

if __name__ == "__main__":
    main()
