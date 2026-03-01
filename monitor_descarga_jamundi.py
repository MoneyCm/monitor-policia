from playwright.sync_api import sync_playwright
import json, re, pandas as pd, os, hashlib, time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

print("="*80)
print("🔍 MONITOR + DESCARGA + ANÁLISIS JAMUNDÍ - DEFINITIVO")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

# Configuración
URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE = Path("mindefensa_monitor_final.json")
OUTPUT_CSV = Path("listado_mindefensa_final.csv")
DOWNLOAD_DIR = Path("workspace")  # Donde se guardarán los archivos descargados
JAMUNDI_CODE = 76364
JAMUNDI_NAMES = ["JAMUNDÍ", "JAMUNDI", "Jamundí", "Jamundi"]

# Archivos que te interesan para el análisis de Jamundí
ARCHIVOS_INTERES = [
    "HOMICIDIO INTENCIONAL.xlsx", "SECUESTRO.xlsx", "EXTORSIÓN.xlsx",
    "HURTO PERSONAS.xlsx", "VIOLENCIA INTRAFAMILIAR.xlsx",
    "DELITOS INFORMÁTICOS.xlsx", "TERRORISMO.xlsx", "MASACRES.xlsx"
]

archivos_encontrados = []
archivos_para_descargar = []

def interceptar_respuesta(response):
    """Captura respuestas JSON de la API de Oracle SCS con URLs de descarga"""
    if response.status != 200:
        return
    content_type = response.headers.get("content-type", "").lower()
    if "json" not in content_type:
        return
    
    try:
        data = response.json()
        buscar_en_json(data, response.url)
    except:
        pass

def buscar_en_json(obj, api_url, nivel=0):
    """Busca recursivamente nombres de archivos .xlsx y sus URLs en JSON"""
    if nivel > 5:
        return
    
    if isinstance(obj, dict):
        # Buscar items de tipo DocumentFile con .xlsx
        if obj.get("type") == "DocumentFile" and "fields" in obj:
            fields = obj.get("fields", {})
            nombre = fields.get("name") or fields.get("filename") or obj.get("name")
            if nombre and str(nombre).upper().endswith(".XLSX"):
                # Construir URL de descarga desde la API
                item_id = obj.get("id")
                if item_id and "content/published/api" in api_url:
                    base_api = api_url.split("?")[0].replace("/items", f"/{item_id}/rendition")
                    download_url = f"{base_api}?channelToken=86fd5ad8af1b4db2b56bfc60a05ec867"
                else:
                    download_url = f"https://www.mindefensa.gov.co/sites/default/files/datos-y-cifras/{nombre.replace(' ', '%20')}"
                
                archivos_encontrados.append({
                    "nombre": str(nombre).strip(),
                    "download_url": download_url,
                    "api_source": api_url[:100],
                    "id": obj.get("id")
                })
        
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                buscar_en_json(value, api_url, nivel+1)
    
    elif isinstance(obj, list):
        for item in obj:
            buscar_en_json(item, api_url, nivel+1)

def descargar_archivo(page, url, nombre_archivo):
    """Descarga un archivo usando la sesión de Playwright (mantiene cookies/auth)"""
    try:
        print(f"   📥 Descargando: {nombre_archivo}...")
        
        # Usar page.request para mantener la sesión del navegador
        response = page.request.get(url, timeout=60000)
        
        if response.status == 200:
            ruta_destino = DOWNLOAD_DIR / nombre_archivo
            with open(ruta_destino, "wb") as f:
                f.write(response.body())
            print(f"   ✅ Guardado: {ruta_destino} ({len(response.body())/1024:.1f} KB)")
            return True
        else:
            print(f"   ❌ Error {response.status}: {url}")
            return False
    except Exception as e:
        print(f"   ❌ Error al descargar: {e}")
        return False

def cargar_estado():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"archivos": {}}

def es_jamundi(valor):
    if pd.isna(valor): return False
    val = str(valor).strip().upper()
    if any(j.upper() in val for j in JAMUNDI_NAMES): return True
    try:
        if int(float(valor)) == JAMUNDI_CODE: return True
    except: pass
    return False

def analizar_jamundi(archivo_path):
    """Analiza un archivo Excel filtrando por Jamundí"""
    try:
        df = pd.read_excel(archivo_path)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Detectar columna de municipio
        col_muni = next((c for c in df.columns if "municipio" in c.lower() or "cod_muni" in c.lower()), None)
        col_fecha = next((c for c in df.columns if "fecha" in c.lower()), None)
        
        if not col_muni:
            return {"error": "No se encontró columna de municipio"}
        
        # Filtrar por Jamundí
        if "cod_muni" in col_muni.lower():
            df_j = df[df[col_muni].astype(str).str.strip() == str(JAMUNDI_CODE)].copy()
        else:
            df_j = df[df[col_muni].astype(str).str.upper().str.contains("JAMUNDI", na=False)].copy()
        
        resultado = {
            "total_original": len(df),
            "total_jamundi": len(df_j),
            "columnas": list(df.columns)
        }
        
        if col_fecha and len(df_j) > 0:
            df_j[col_fecha] = pd.to_datetime(df_j[col_fecha], errors='coerce')
            años = sorted(df_j[col_fecha].dropna().dt.year.unique().astype(int).tolist())
            resultado["años"] = años
            if len(años) >= 2:
                anual = df_j.groupby(df_j[col_fecha].dt.year).size()
                primera, ultima = anual.iloc[0], anual.iloc[-1]
                cambio = ((ultima - primera) / primera * 100) if primera != 0 else 0
                resultado["tendencia"] = "📈 ALZA" if cambio > 10 else "📉 BAJA" if cambio < -10 else "➡️ ESTABLE"
        
        return resultado
        
    except Exception as e:
        return {"error": str(e)}

def main():
    print("🚀 Iniciando monitoreo + descarga + análisis...")
    
    # === FASE 1: Detectar archivos ===
    print("\n📡 FASE 1: Detectando archivos en MinDefensa...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        page.on("response", interceptar_respuesta)
        
        print(f"   🌐 Navegando a: {URL}")
        page.goto(URL, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(5000)
        
        # Scroll para trigger de lazy-loading
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
            unicos.append(a)
    
    print(f"   ✅ Encontrados {len(unicos)} archivos")
    
    # === FASE 2: Comparar con estado anterior ===
    print("\n🔍 FASE 2: Comparando con estado anterior...")
    estado = cargar_estado()
    previos = estado.get("archivos", {})
    
    nuevos = [a for a in unicos if a["nombre"] not in previos]
    actualizados = [a for a in unicos if a["nombre"] in previos]  # Podríamos comparar hash si quisiéramos
    
    archivos_para_descargar = nuevos + actualizados[:5]  # Limitar a 5 actualizados para no saturar
    
    print(f"   🆕 Nuevos: {len(nuevos)}")
    print(f"   🔄 Actualizados (procesando primeros 5): {min(5, len(actualizados))}")
    
    # === FASE 3: Descargar archivos ===
    if archivos_para_descargar:
        print(f"\n📥 FASE 3: Descargando {len(archivos_para_descargar)} archivos...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto(URL, wait_until='networkidle', timeout=30000)
            
            descargados = 0
            for arch in archivos_para_descargar:
                if descargar_archivo(page, arch["download_url"], arch["nombre"]):
                    descargados += 1
                    # Si es un archivo de interés, analizar Jamundí
                    if any(inter in arch["nombre"].upper() for inter in [i.upper() for i in ARCHIVOS_INTERES]):
                        print(f"   🔍 Analizando Jamundí en {arch['nombre']}...")
                        resultado = analizar_jamundi(DOWNLOAD_DIR / arch["nombre"])
                        if "error" not in resultado:
                            print(f"      📊 Jamundí: {resultado['total_jamundi']:,} de {resultado['total_original']:,} registros")
                            if "años" in resultado:
                                print(f"      📅 Años: {resultado['años']}")
                            if "tendencia" in resultado:
                                print(f"      📈 Tendencia: {resultado['tendencia']}")
                        else:
                            print(f"      ⚠️ Error en análisis: {resultado['error']}")
            
            browser.close()
            print(f"   ✅ Descargas completadas: {descargados}/{len(archivos_para_descargar)}")
    
    # === FASE 4: Guardar estado y generar informe ===
    print("\n💾 FASE 4: Guardando estado y generando informe...")
    
    estado["ultima_revision"] = datetime.now().isoformat()
    estado["archivos"] = {a["nombre"]: {"url": a["download_url"], "detectado": datetime.now().isoformat()} for a in unicos}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    
    df = pd.DataFrame(unicos)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    # Generar informe rápido de Jamundí si hay datos
    informe_jamundi = []
    for archivo in DOWNLOAD_DIR.glob("*.xlsx"):
        if any(inter in archivo.name.upper() for inter in [i.upper() for i in ARCHIVOS_INTERES]):
            resultado = analizar_jamundi(archivo)
            if "total_jamundi" in resultado:
                informe_jamundi.append({
                    "archivo": archivo.name,
                    "jamundi": resultado["total_jamundi"],
                    "total": resultado["total_original"],
                    "años": resultado.get("años", []),
                    "tendencia": resultado.get("tendencia", "N/A")
                })
    
    if informe_jamundi:
        informe_path = DOWNLOAD_DIR / "resumen_jamundi_actualizado.txt"
        with open(informe_path, 'w', encoding='utf-8') as f:
            f.write("RESUMEN JAMUNDÍ - ACTUALIZACIÓN AUTOMÁTICA\n")
            f.write(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write("="*60 + "\n\n")
            for item in sorted(informe_jamundi, key=lambda x: x["jamundi"], reverse=True):
                f.write(f"📁 {item['archivo']}\n")
                f.write(f"   • Registros Jamundí: {item['jamundi']:,} / {item['total']:,}\n")
                if item['años']:
                    f.write(f"   • Años: {item['años']}\n")
                f.write(f"   • Tendencia: {item['tendencia']}\n\n")
        print(f"   📄 Informe Jamundí guardado: {informe_path}")
    
    print(f"\n💾 Listado guardado: {OUTPUT_CSV}")
    print(f"💾 Estado guardado: {STATE_FILE}")
    
    # Resumen final
    print("\n" + "="*80)
    print("✅ PROCESO COMPLETADO")
    print("="*80)
    if archivos_para_descargar:
        print(f"📥 Archivos descargados: {len(archivos_para_descargar)}")
        print(f"📊 Archivos de Jamundí analizados: {len(informe_jamundi)}")
        print(f"\n🎯 Próxima revisión automática: configurá Task Scheduler para ejecutar este script semanalmente")
    else:
        print(f"✅ Sin cambios desde la última revisión ({estado.get('ultima_revision', 'desconocida')})")
        print(f"💡 Los archivos ya están actualizados en tu workspace")

if __name__ == "__main__":
    main()
