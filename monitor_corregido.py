from playwright.sync_api import sync_playwright
import json, re, pandas as pd, os, hashlib, time, shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

print("="*80)
print("🔍 MONITOR + DESCARGA + JAMUNDÍ - VERSIÓN CORREGIDA")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

# Configuración
URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE = Path("mindefensa_monitor_final.json")
OUTPUT_CSV = Path("listado_mindefensa_final.csv")
DOWNLOAD_DIR = Path("workspace")
JAMUNDI_CODE = 76364
JAMUNDI_NAMES = ["JAMUNDÍ", "JAMUNDI", "Jamundí", "Jamundi"]

ARCHIVOS_INTERES = [
    "HOMICIDIO INTENCIONAL.xlsx", "SECUESTRO.xlsx", "EXTORSIÓN.xlsx",
    "HURTO PERSONAS.xlsx", "VIOLENCIA INTRAFAMILIAR.xlsx",
    "DELITOS INFORMÁTICOS.xlsx", "TERRORISMO.xlsx", "MASACRES.xlsx"
]

archivos_encontrados = []

def interceptar_respuesta(response):
    """Captura respuestas JSON de Oracle SCS"""
    if response.status != 200:
        return
    if "json" not in response.headers.get("content-type", "").lower():
        return
    try:
        data = response.json()
        buscar_en_json(data)
    except:
        pass

def buscar_en_json(obj, nivel=0):
    """Busca archivos .xlsx en estructuras JSON"""
    if nivel > 5:
        return
    if isinstance(obj, dict):
        if obj.get("type") == "DocumentFile" and "fields" in obj:
            fields = obj.get("fields", {})
            nombre = fields.get("name") or fields.get("filename") or obj.get("name")
            if nombre and str(nombre).upper().endswith(".XLSX"):
                # URL directa simplificada (funciona para MinDefensa)
                nombre_limpio = str(nombre).strip()
                download_url = f"https://www.mindefensa.gov.co/sites/default/files/datos-y-cifras/{quote(nombre_limpio)}"
                
                archivos_encontrados.append({
                    "nombre": nombre_limpio,
                    "download_url": download_url,
                    "id": obj.get("id")
                })
        for value in obj.values():
            if isinstance(value, (dict, list)):
                buscar_en_json(value, nivel+1)
    elif isinstance(obj, list):
        for item in obj:
            buscar_en_json(item, nivel+1)

def descargar_archivo_simple(url, nombre_archivo, intentos=3):
    """Descarga usando requests estándar (más confiable para URLs directas)"""
    import requests
    for intento in range(intentos):
        try:
            print(f"   📥 Intento {intento+1}: {nombre_archivo}...")
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
            
            if response.status_code == 200 and len(response.content) > 1000:
                ruta = DOWNLOAD_DIR / nombre_archivo
                with open(ruta, "wb") as f:
                    f.write(response.content)
                print(f"   ✅ Guardado: {ruta.name} ({len(response.content)/1024:.1f} KB)")
                return True
            else:
                print(f"   ⚠️ Status {response.status_code} o contenido muy pequeño, reintentando...")
                time.sleep(2)
        except Exception as e:
            print(f"   ⚠️ Error intento {intento+1}: {e}")
            time.sleep(2)
    print(f"   ❌ No se pudo descargar después de {intentos} intentos")
    return False

def cargar_estado():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"archivos": {}}

def es_jamundi(valor):
    if pd.isna(valor): return False
    val = str(valor).strip().upper()
    return any(j.upper() in val for j in JAMUNDI_NAMES) or (str(valor).strip() == str(JAMUNDI_CODE))

def analizar_jamundi(archivo_path):
    """Analiza un Excel filtrando por Jamundí"""
    try:
        df = pd.read_excel(archivo_path)
        df.columns = [c.lower().strip() for c in df.columns]
        
        col_muni = next((c for c in df.columns if "municipio" in c.lower() or "cod_muni" in c.lower()), None)
        col_fecha = next((c for c in df.columns if "fecha" in c.lower()), None)
        
        if not col_muni:
            return {"error": "No se encontró columna de municipio"}
        
        if "cod_muni" in col_muni.lower():
            df_j = df[df[col_muni].astype(str).str.strip() == str(JAMUNDI_CODE)].copy()
        else:
            df_j = df[df[col_muni].astype(str).str.upper().str.contains("JAMUNDI", na=False)].copy()
        
        resultado = {"total_original": len(df), "total_jamundi": len(df_j), "columnas": list(df.columns)}
        
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

def guardar_csv_seguro(df, ruta, max_intentos=5):
    """Guarda CSV manejando archivos bloqueados"""
    for intento in range(max_intentos):
        try:
            df.to_csv(ruta, index=False, encoding='utf-8-sig')
            return True
        except PermissionError:
            print(f"   ⚠️ Archivo bloqueado, esperando 2s (intento {intento+1})...")
            time.sleep(2)
            # Si sigue bloqueado, usar nombre alternativo
            if intento == max_intentos - 1:
                ruta_alt = ruta.with_stem(f"{ruta.stem}_{datetime.now().strftime('%H%M%S')}")
                print(f"   💡 Usando nombre alternativo: {ruta_alt.name}")
                df.to_csv(ruta_alt, index=False, encoding='utf-8-sig')
                return True
    return False

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
    
    # === FASE 2: Comparar con estado ===
    print("\n🔍 FASE 2: Comparando con estado anterior...")
    estado = cargar_estado()
    previos = estado.get("archivos", {})
    
    nuevos = [a for a in unicos if a["nombre"] not in previos]
    actualizados = [a for a in unicos if a["nombre"] in previos]
    
    archivos_para_descargar = nuevos + actualizados[:5]
    
    print(f"   🆕 Nuevos: {len(nuevos)}")
    print(f"   🔄 Actualizados (procesando primeros 5): {min(5, len(actualizados))}")
    
    # === FASE 3: Descargar ===
    if archivos_para_descargar:
        print(f"\n📥 FASE 3: Descargando {len(archivos_para_descargar)} archivos...")
        descargados = 0
        
        for arch in archivos_para_descargar:
            if descargar_archivo_simple(arch["download_url"], arch["nombre"]):
                descargados += 1
                if any(inter in arch["nombre"].upper() for inter in [i.upper() for i in ARCHIVOS_INTERES]):
                    print(f"   🔍 Analizando Jamundí en {arch['nombre']}...")
                    resultado = analizar_jamundi(DOWNLOAD_DIR / arch["nombre"])
                    if "error" not in resultado:
                        print(f"      📊 Jamundí: {resultado['total_jamundi']:,} de {resultado['total_original']:,}")
                        if "años" in resultado:
                            print(f"      📅 Años: {resultado['años']}")
                        if "tendencia" in resultado:
                            print(f"      📈 Tendencia: {resultado['tendencia']}")
                    else:
                        print(f"      ⚠️ Error análisis: {resultado['error']}")
        
        print(f"   ✅ Descargas completadas: {descargados}/{len(archivos_para_descargar)}")
    
    # === FASE 4: Guardar estado ===
    print("\n💾 FASE 4: Guardando estado...")
    
    estado["ultima_revision"] = datetime.now().isoformat()
    estado["archivos"] = {a["nombre"]: {"url": a["download_url"], "detectado": datetime.now().isoformat()} for a in unicos}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    
    # Guardar CSV con manejo de bloqueo
    df = pd.DataFrame(unicos)
    if guardar_csv_seguro(df, OUTPUT_CSV):
        print(f"   ✅ Listado guardado: {OUTPUT_CSV}")
    
    # Generar informe Jamundí
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
        print(f"   📄 Informe Jamundí: {informe_path}")
    
    # Resumen final
    print("\n" + "="*80)
    print("✅ PROCESO COMPLETADO")
    print("="*80)
    if archivos_para_descargar:
        print(f"📥 Descargados: {descargados}/{len(archivos_para_descargar)}")
        print(f"📊 Jamundí analizados: {len(informe_jamundi)}")
    else:
        print(f"✅ Sin cambios desde: {estado.get('ultima_revision', 'desconocida')}")

if __name__ == "__main__":
    main()
